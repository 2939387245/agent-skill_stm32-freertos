# 外设驱动模板

本文档包含 UART、ADC、I2C、printf 重定向等外设驱动的完整模板代码。

---

## 2.1 UART DMA + 队列 + IDLE 中断

### 头文件（uart_driver.h）

```c
#ifndef UART_DRIVER_H
#define UART_DRIVER_H

#include "main.h"
#include "FreeRTOS.h"
#include "queue.h"

#define UART_RX_BUFFER_SIZE 256

typedef struct {
    uint8_t data[UART_RX_BUFFER_SIZE];
    uint16_t length;
} UartRxMessage_t;

extern QueueHandle_t g_uart_rx_queue;

void vUartDriverInit(void);
void vUartRxTask(void *pvParameters);

#endif /* UART_DRIVER_H */
```

### 实现文件（uart_driver.c）

```c
#include "uart_driver.h"
#include "string.h"
#include "stdio.h"

static uint8_t g_rx_buffer[UART_RX_BUFFER_SIZE];
static volatile uint16_t g_rx_index = 0;
static volatile uint8_t g_rx_complete = 0;

QueueHandle_t g_uart_rx_queue;

void vUartDriverInit(void)
{
    /* 使能 IDLE 中断 */
    __HAL_UART_ENABLE_IT(&huart1, UART_IT_IDLE);

    /* 启动 DMA 接收 */
    HAL_UART_Receive_DMA(&huart1, g_rx_buffer, UART_RX_BUFFER_SIZE);

    /* 创建队列 */
    g_uart_rx_queue = xQueueCreate(20, sizeof(UartRxMessage_t));
}

void HAL_UART_IDLECallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1)
    {
        /* 计算接收长度 */
        uint16_t dma_counter = __HAL_DMA_GET_COUNTER(&hdma_usart1_rx);
        g_rx_index = UART_RX_BUFFER_SIZE - dma_counter;
        g_rx_complete = 1;

        /* 停止 DMA */
        HAL_UART_DMAStop(&huart1);
    }
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1)
    {
        g_rx_index = UART_RX_BUFFER_SIZE;
        g_rx_complete = 1;
        HAL_UART_DMAStop(&huart1);
    }
}

void vUartRxTask(void *pvParameters)
{
    UartRxMessage_t msg;

    while (1)
    {
        /* 等待数据接收完成 */
        while (g_rx_complete == 0)
        {
            vTaskDelay(pdMS_TO_TICKS(10));
        }

        /* 复制数据 */
        memcpy(msg.data, g_rx_buffer, g_rx_index);
        msg.length = g_rx_index;

        /* 发送到队列 */
        if (xQueueSend(g_uart_rx_queue, &msg, 0) == pdTRUE)
        {
            /* 重新启动 DMA */
            g_rx_complete = 0;
            HAL_UART_Receive_DMA(&huart1, g_rx_buffer,
                                 UART_RX_BUFFER_SIZE);
        }
        else
        {
            printf("队列满，丢弃数据\r\n");
            g_rx_complete = 0;
            HAL_UART_Receive_DMA(&huart1, g_rx_buffer,
                                 UART_RX_BUFFER_SIZE);
        }
    }
}

/* 数据处理任务示例 */
void vDataProcessTask(void *pvParameters)
{
    UartRxMessage_t msg;

    while (1)
    {
        if (xQueueReceive(g_uart_rx_queue, &msg, portMAX_DELAY) == pdTRUE)
        {
            printf("收到 %d 字节数据: ", msg.length);

            /* 回显数据 */
            for (int i = 0; i < msg.length; i++)
            {
                printf("%02X ", msg.data[i]);
            }
            printf("\r\n");
        }
    }
}
```

---

## 2.2 ADC DMA + 任务通知

### 头文件（adc_driver.h）

```c
#ifndef ADC_DRIVER_H
#define ADC_DRIVER_H

#include "main.h"
#include "FreeRTOS.h"
#include "task.h"

#define ADC_CHANNEL_COUNT 3

extern TaskHandle_t g_adc_task_handle;
extern uint32_t g_adc_values[ADC_CHANNEL_COUNT];

void MX_ADC1_Init(void);
void vAdcTask(void *pvParameters);

#endif /* ADC_DRIVER_H */
```

### 实现文件（adc_driver.c）

```c
#include "adc_driver.h"
#include "string.h"

#define ADC_BUFFER_SIZE ADC_CHANNEL_COUNT

static uint32_t g_adc_buffer[ADC_BUFFER_SIZE];
uint32_t g_adc_values[ADC_CHANNEL_COUNT];
TaskHandle_t g_adc_task_handle;

void MX_ADC1_Init(void)
{
    ADC_ChannelConfTypeDef sConfig = {0};

    /* 配置 ADC */
    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV4;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.ScanConvMode = ENABLE;
    hadc1.Init.ContinuousConvMode = ENABLE;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.NbrOfConversion = ADC_CHANNEL_COUNT;
    hadc1.Init.DMAContinuousRequests = ENABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SEQ_CONV;

    HAL_ADC_Init(&hadc1);

    /* 配置通道 */
    sConfig.Channel = ADC_CHANNEL_0;
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_480CYCLES;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);

    sConfig.Channel = ADC_CHANNEL_1;
    sConfig.Rank = 2;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);

    sConfig.Channel = ADC_CHANNEL_2;
    sConfig.Rank = 3;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);

    /* 启动 DMA */
    HAL_ADC_Start_DMA(&hadc1, g_adc_buffer, ADC_BUFFER_SIZE);
}

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1)
    {
        /* 复制数据 */
        memcpy(g_adc_values, g_adc_buffer, sizeof(g_adc_values));

        /* 发送任务通知 */
        BaseType_t xHigherPriorityTaskWoken = pdFALSE;
        vTaskNotifyGiveFromISR(g_adc_task_handle,
                               &xHigherPriorityTaskWoken);
        portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
    }
}

void vAdcTask(void *pvParameters)
{
    uint32_t tick_count = 0;
    float voltage;

    while (1)
    {
        /* 等待 ADC 转换完成 */
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        tick_count++;

        /* 处理 ADC 数据 */
        printf("ADC 采样 #%lu:\r\n", tick_count);

        for (int i = 0; i < ADC_CHANNEL_COUNT; i++)
        {
            /* 转换为电压值 */
            voltage = (float)g_adc_values[i] * 3.3f / 4095.0f;
            printf("  CH%d: %.3f V (0x%04lX)\r\n",
                   i, voltage, g_adc_values[i]);
        }
        printf("\r\n");
    }
}
```

---

## 2.3 I2C 传感器读取（BME280）

### 头文件（bme280_driver.h）

```c
#ifndef BME280_DRIVER_H
#define BME280_DRIVER_H

#include "main.h"
#include "FreeRTOS.h"
#include "queue.h"

#define BME280_ADDR 0x76

typedef struct {
    float temperature;   /* 温度 */
    float humidity;      /* 湿度 */
    float pressure;      /* 气压 */
} Bme280Data_t;

extern QueueHandle_t g_bme280_queue;

void vBme280Task(void *pvParameters);
HAL_StatusTypeDef BME280_Init(I2C_HandleTypeDef *hi2c);
HAL_StatusTypeDef BME280_Read(I2C_HandleTypeDef *hi2c, Bme280Data_t *data);

#endif /* BME280_DRIVER_H */
```

### 实现文件（bme280_driver.c）

```c
#include "bme280_driver.h"
#include "string.h"

#define BME280_REG_ID      0xD0
#define BME280_REG_RESET   0xE0
#define BME280_REG_CTRL_HUM 0xF2
#define BME280_REG_CTRL_MEAS 0xF4
#define BME280_REG_CONFIG  0xF5
#define BME280_REG_DATA   0xF7

static uint8_t g_tx_buffer[4];
static uint8_t g_rx_buffer[8];
static int32_t g_compensate_t;
static uint32_t g_compensate_p;
static uint32_t g_compensate_h;

QueueHandle_t g_bme280_queue;

HAL_StatusTypeDef BME280_Init(I2C_HandleTypeDef *hi2c)
{
    uint8_t id;

    /* 读取芯片 ID */
    g_tx_buffer[0] = BME280_REG_ID;
    HAL_I2C_Master_Transmit(hi2c, BME280_ADDR << 1,
                            g_tx_buffer, 1, 100);
    HAL_I2C_Master_Receive(hi2c, BME280_ADDR << 1,
                           &id, 1, 100);

    if (id != 0x60)
    {
        return HAL_ERROR;
    }

    /* 软件复位 */
    g_tx_buffer[0] = BME280_REG_RESET;
    g_tx_buffer[1] = 0xB6;
    HAL_I2C_Master_Transmit(hi2c, BME280_ADDR << 1,
                            g_tx_buffer, 2, 100);
    vTaskDelay(pdMS_TO_TICKS(10));

    /* 配置湿度采样 */
    g_tx_buffer[0] = BME280_REG_CTRL_HUM;
    g_tx_buffer[1] = 0x05;  /* 16x 过采样 */
    HAL_I2C_Master_Transmit(hi2c, BME280_ADDR << 1,
                            g_tx_buffer, 2, 100);

    /* 配置测量 */
    g_tx_buffer[0] = BME280_REG_CTRL_MEAS;
    g_tx_buffer[1] = 0xB7;  /* 温度 16x + 压力 16x */
    HAL_I2C_Master_Transmit(hi2c, BME280_ADDR << 1,
                            g_tx_buffer, 2, 100);

    /* 配置过滤器 */
    g_tx_buffer[0] = BME280_REG_CONFIG;
    g_tx_buffer[1] = 0x00;  /* 无过滤器 */
    HAL_I2C_Master_Transmit(hi2c, BME280_ADDR << 1,
                            g_tx_buffer, 2, 100);

    return HAL_OK;
}

/* 简化的补偿计算（实际应使用 BME280 官方算法） */
static void BME280_Compensate(int32_t adc_t, int32_t adc_p,
                              int32_t adc_h)
{
    g_compensate_t = adc_t / 100;
    g_compensate_p = adc_p / 256;
    g_compensate_h = adc_h / 1024;
}

HAL_StatusTypeDef BME280_Read(I2C_HandleTypeDef *hi2c, Bme280Data_t *data)
{
    /* 发送数据寄存器地址 */
    g_tx_buffer[0] = BME280_REG_DATA;
    HAL_I2C_Master_Transmit(hi2c, BME280_ADDR << 1,
                            g_tx_buffer, 1, 100);

    /* 读取 8 字节数据 */
    HAL_I2C_Master_Receive(hi2c, BME280_ADDR << 1,
                           g_rx_buffer, 8, 100);

    /* 解析数据 */
    int32_t adc_p = (g_rx_buffer[0] << 12) | (g_rx_buffer[1] << 4) |
                    (g_rx_buffer[2] >> 4);
    int32_t adc_t = (g_rx_buffer[3] << 12) | (g_rx_buffer[4] << 4) |
                    (g_rx_buffer[5] >> 4);
    int32_t adc_h = (g_rx_buffer[6] << 8) | g_rx_buffer[7];

    /* 补偿计算 */
    BME280_Compensate(adc_t, adc_p, adc_h);

    /* 填充结果 */
    data->temperature = (float)g_compensate_t / 100.0f;
    data->pressure = (float)g_compensate_p / 256.0f;
    data->humidity = (float)g_compensate_h / 1024.0f;

    return HAL_OK;
}

void vBme280Task(void *pvParameters)
{
    Bme280Data_t sensor_data;
    I2C_HandleTypeDef *hi2c1 = (I2C_HandleTypeDef *)pvParameters;

    /* 初始化传感器 */
    while (BME280_Init(hi2c1) != HAL_OK)
    {
        printf("BME280 初始化失败，重试...\r\n");
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
    printf("BME280 初始化成功\r\n");

    /* 创建队列 */
    g_bme280_queue = xQueueCreate(5, sizeof(Bme280Data_t));

    while (1)
    {
        /* 读取传感器 */
        if (BME280_Read(hi2c1, &sensor_data) == HAL_OK)
        {
            printf("温度: %.1f°C, 湿度: %.1f%%, 气压: %.1f hPa\r\n",
                   sensor_data.temperature,
                   sensor_data.humidity,
                   sensor_data.pressure);

            /* 发送到队列 */
            xQueueSend(g_bme280_queue, &sensor_data, 0);
        }
        else
        {
            printf("BME280 读取失败\r\n");
        }

        vTaskDelay(pdMS_TO_TICKS(2000));  /* 0.5Hz 采样 */
    }
}
```

---

## 2.4 printf 重定向（ITM_SendChar）

### 头文件（retarget.h）

```c
#ifndef RETARGET_H
#define RETARGET_H

#include <stdio.h>

/* 重定向函数声明 */
int __attribute__((weak)) _write(int file, char *ptr, int len);

/* ITM 调试输出宏 */
#define ITM_Port8(n)    (*((volatile unsigned char *)(0xE0000000 + 4 * n)))
#define ITM_Port16(n)   (*((volatile unsigned short *)(0xE0000000 + 4 * n)))
#define ITM_Port32(n)   (*((volatile unsigned long *)(0xE0000000 + 4 * n)))
#define DEMCR           (*((volatile unsigned long *)(0xE000EDFC)))
#define TRCENA          0x01000000

#endif /* RETARGET_H */
```

### 实现文件（retarget.c）

```c
#include "retarget.h"
#include "core_cm4.h"

/* ITM 调试输出初始化 */
void ITM_Init(void)
{
    /* 使能 TRACE 调试 */
    DEMCR |= TRCENA;

    /* 配置 SWO 引脚（根据具体芯片） */
    /* 此处省略 GPIO 配置，ST-Link 默认配置 SWO */

    /* 设置 ITM 端口 0 */
    ITM->TCR = 0x00000009;  /* ITMENA | ATVALID */
    ITM->TER = 0x00000001;  /* 使能端口 0 */
}

/* 重定向 fputc 到 ITM */
int __attribute__((weak)) _write(int file, char *ptr, int len)
{
    (void)file;

    for (int i = 0; i < len; i++)
    {
        /* 等待 SWO 端口就绪 */
        while (ITM->PORT[0].u32 == 0) {}
        ITM->PORT[0].u8 = (uint8_t)ptr[i];
    }

    return len;
}

/* 重定向 puts */
int __attribute__((weak)) _puts(const char *str)
{
    int i = 0;
    while (str[i])
    {
        if (str[i] == '\n')
        {
            ITM_Port8(0) = '\r';
            while (ITM_Port8(0) == 0) {}
        }
        ITM_Port8(0) = str[i];
        while (ITM_Port8(0) == 0) {}
        i++;
    }
    return i;
}

/* 使用示例 */
void vItmExampleTask(void *pvParameters)
{
    ITM_Init();

    while (1)
    {
        printf("Hello from ITM! Tick: %lu\r\n", HAL_GetTick());
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```
