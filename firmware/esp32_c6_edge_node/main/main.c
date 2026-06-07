#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <strings.h>

#include "driver/gpio.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"
#include "mqtt_client.h"
#include "nvs_flash.h"

#define NODE_ID "esp32c6_load_01"
#define WIFI_SSID "WIFI_SSID"
#define WIFI_PASSWORD "WIFI_PASSWORD"
#define RELAY_GPIO GPIO_NUM_4
#define TELEMETRY_PERIOD_US (5LL * 1000LL * 1000LL)
#define WIFI_CONNECTED_BIT BIT0

static const char *TAG = "ems_edge";
static esp_mqtt_client_handle_t mqtt_client;
static EventGroupHandle_t wifi_event_group;
static bool relay_state;

static void publish_telemetry(void)
{
    if (mqtt_client == NULL) {
        return;
    }

    char topic[96];
    char payload[160];
    int64_t uptime_s = esp_timer_get_time() / 1000000LL;

    snprintf(topic, sizeof(topic), "ems/edge/%s/telemetry", NODE_ID);
    snprintf(
        payload,
        sizeof(payload),
        "{\"node\":\"%s\",\"uptime_s\":%lld,\"relay\":%s}",
        NODE_ID,
        uptime_s,
        relay_state ? "true" : "false"
    );

    esp_mqtt_client_publish(mqtt_client, topic, payload, 0, 1, 0);
}

static void set_relay(bool enabled)
{
    relay_state = enabled;
    gpio_set_level(RELAY_GPIO, enabled ? 1 : 0);
    publish_telemetry();
}

static void handle_command(const char *topic, int topic_len, const char *data, int data_len)
{
    char topic_buf[128] = {0};
    char data_buf[64] = {0};

    snprintf(topic_buf, sizeof(topic_buf), "%.*s", topic_len, topic);
    snprintf(data_buf, sizeof(data_buf), "%.*s", data_len, data);

    ESP_LOGI(TAG, "Command topic=%s payload=%s", topic_buf, data_buf);

    if (strstr(topic_buf, "/cmd/relay") == NULL) {
        return;
    }

    if (strcasecmp(data_buf, "ON") == 0 || strcmp(data_buf, "1") == 0) {
        set_relay(true);
    } else if (strcasecmp(data_buf, "OFF") == 0 || strcmp(data_buf, "0") == 0) {
        set_relay(false);
    }
}

static void mqtt_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
{
    esp_mqtt_event_handle_t event = event_data;

    switch ((esp_mqtt_event_id_t)event_id) {
    case MQTT_EVENT_CONNECTED: {
        char command_topic[96];
        snprintf(command_topic, sizeof(command_topic), "ems/edge/%s/cmd/#", NODE_ID);
        ESP_LOGI(TAG, "MQTT connected; subscribing to %s", command_topic);
        esp_mqtt_client_subscribe(event->client, command_topic, 1);
        publish_telemetry();
        break;
    }
    case MQTT_EVENT_DATA:
        handle_command(event->topic, event->topic_len, event->data, event->data_len);
        break;
    case MQTT_EVENT_DISCONNECTED:
        ESP_LOGW(TAG, "MQTT disconnected");
        break;
    default:
        break;
    }
}

static void configure_relay_gpio(void)
{
    gpio_config_t io_conf = {
        .pin_bit_mask = 1ULL << RELAY_GPIO,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };

    gpio_config(&io_conf);
    set_relay(false);
}

static void wifi_event_handler(void *arg, esp_event_base_t event_base, int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGW(TAG, "Wi-Fi disconnected; retrying");
        esp_wifi_connect();
        xEventGroupClearBits(wifi_event_group, WIFI_CONNECTED_BIT);
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Wi-Fi connected, IP=" IPSTR, IP2STR(&event->ip_info.ip));
        xEventGroupSetBits(wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

static void connect_wifi(void)
{
    wifi_event_group = xEventGroupCreate();

    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        WIFI_EVENT,
        ESP_EVENT_ANY_ID,
        &wifi_event_handler,
        NULL,
        NULL
    ));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        IP_EVENT,
        IP_EVENT_STA_GOT_IP,
        &wifi_event_handler,
        NULL,
        NULL
    ));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID,
            .password = WIFI_PASSWORD,
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    xEventGroupWaitBits(wifi_event_group, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);
}

static void start_mqtt(void)
{
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = "mqtt://MQTT_BROKER_IP",
    };

    mqtt_client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_register_event(mqtt_client, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL);
    esp_mqtt_client_start(mqtt_client);
}

void app_main(void)
{
    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    configure_relay_gpio();

    connect_wifi();
    start_mqtt();

    int64_t next_publish = esp_timer_get_time();
    while (true) {
        int64_t now = esp_timer_get_time();
        if (now >= next_publish) {
            publish_telemetry();
            next_publish = now + TELEMETRY_PERIOD_US;
        }
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
