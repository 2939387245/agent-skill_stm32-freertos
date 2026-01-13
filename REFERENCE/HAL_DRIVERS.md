# HAL 外设驱动集成

本文档介绍 UART、ADC、I2C、TIM 等外设与 FreeRTOS 的集成方法。

---

## UART DMA + 队列（IDLE 中断）

### 头文件（uart_rx.h）

```c
#ifndef UART_RX_H
#define UART_RX_H

#include "main.h"
#include "FreeRTOS.h"
#include "queue.h"

#define UART_RX_BUFFER_SIZE 256

typedef struct {
    uint8_t data[UART_RX_BUFFER_SIZE];
    uint16_t length;
} UartRxMessage_t;

extern QueueHandle_t g_uart_rx_queue;
extern TaskHandle_t g_uart_task_handle;

void vUartRxTask(void *pvParameters);
void MX_UART1_Init(void);
void HAL_UART_IDLECallback(UART_HandleTypeDef *huart);
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart);

#endif /* UART_RX_H */
```

### 实现文件（uart_rx.c）

```c
#include "uart_rx.h"
#include "dma.h"

static uint8_t g_rx_buffer[UART_RX_BUFFER_SIZE];
static uint8_t g_rx_temp[UART_RX_BUFFER_SIZE];
static volatile uint16_t g_rx_length = 0;
static volatile uint8_t g_rx_flag = 0;

QueueHandle_t g_uart_rx_queue;
TaskHandle_t g_uart_task_handle;

void MX_UART1_Init(void)
{
    /* 使能 IDLE 中断和 DMA */
    __HAL_UART_ENABLE_IT(&huart1, UART_IT_IDLE);
    HAL_UART_Receive_DMA(&huart1, g_rx_buffer, UART_RX_BUFFER_SIZE);

    /* 创建队列 */
    g_uart_rx_queue = xQueueCreate(10, sizeof(UartRxMessage_t));
}

void HAL_UART_IDLECallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1)
    {
        /* 计算接收长度 */
        uint16_t dma_counter = __HAL_DMA_GET_COUNTER(&hdma_usart1_rx);
        g_rx_length = UART_RX_BUFFER_SIZE - dma_counter;
        g_rx_flag = 1;

        /* 停止 DMA */
        HAL_UART_DMAStop(&huart1);
    }
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1)
    {
        g_rx_length = UART_RX_BUFFER_SIZE;
        g_rx_flag = 1;
    }
}

void vUartRxTask(void *pvParameters)
{
    UartRxMessage_t rx_msg;

    while (1)
    {
        /* 等待数据就绪 */
        while (g_rx_flag == 0)
        {
            vTaskDelay(pdMS_TO_TICKS(10));
        }

        /* 复制数据 */
        memcpy(rx_msg.data, g_rx_buffer, g_rx_length);
        rx_msg.length = g_rx_length;

        /* 发送到队列 */
        if (xQueueSend(g_uart_rx_queue, &rx_msg, 0) == pdTRUE)
        {
            /* 发送成功，重新启动 DMA */
            g_rx_flag = 0;
            HAL_UART_Receive_DMA(&huart1, g_rx_buffer,
                                 UART_RX_BUFFER_SIZE);
        }
        else
        {
            /* 队列满，丢弃数据 */
            g_rx_flag = 0;
            HAL_UART_Receive_DMA(&huart1, g_rx_buffer,
                                 UART_RX_BUFFER_SIZE);
        }
    }
}
```

---

## ADC DMA + 任务通知

### 头文件（adc_process.h）

```c
#ifndef ADC_PROCESS_H
#define ADC_PROCESS_H

#include "main.h"
#include "FreeRTOS.h"
#include "task.h"

#define ADC_CHANNEL_NUM 3
#define ADC_BUFFER_SIZE ADC_CHANNEL_NUM

extern TaskHandle_t g_adc_task_handle;
extern uint32_t g_adc_values[ADC_CHANNEL_NUM];

void vAdcProcessTask(void *pvParameters);
void MX_ADC1_Init(void);

#endif /* ADC_PROCESS_H */
```

### 实现文件（adc_process.c）

```c
#include "adc_process.h"
#include "dma.h"

static uint32_t g_adc_buffer[ADC_BUFFER_SIZE];
uint32_t g_adc_values[ADC_CHANNEL_NUM];
TaskHandle_t g_adc_task_handle;

void MX_ADC1_Init(void)
{
    /* 配置 ADC DMA */
    HAL_ADC_Start_DMA(&hadc1, g_adc_buffer, ADC_BUFFER_SIZE);
}

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1)
    {
        /* 复制数据 */
        for (int i = 0; i < ADC_CHANNEL_NUM; i++)
        {
            g_adc_values[i] = g_adc_buffer[i];
        }

        /* 发送任务通知 */
        BaseType_t xHigherPriorityTaskWoken = pdFALSE;
        vTaskNotifyGiveFromISR(g_adc_task_handle,
                               &xHigherPriorityTaskWoken);
        portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
    }
}

void vAdcProcessTask(void *pvParameters)
{
    uint32_t notification_value;
    uint32_t adc_raw;

    while (1)
    {
        /* 等待 ADC 转换完成通知 */
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        /* 处理 ADC 数据 */
        for (int i = 0; i < ADC_CHANNEL_NUM; i++)
        {
            adc_raw = g_adc_values[i];
            /* 转换为电压值（假设 3.3V 参考） */
            float voltage = (float)adc_raw * 3.3f / 4095.0f;

            /* 发送数据到其他任务或输出 */
            printf("CH%d: %.3f V\r\n", i, voltage);
        }
    }
}
```

---

## I2C 传感器读取

### 头文件（i2c_sensor.h）

```c
#ifndef I2C_SENSOR_H
#define I2C_SENSOR_H

#include "main.h"
#include "FreeRTOS.h"
#include "queue.h"

#define I2C_SENSOR_ADDR 0x68  /* MPU6050 地址 */

typedef struct {
    int16_t acc_x, acc_y, acc_z;
    int16_t gyro_x, gyro_y, gyro_z;
} Mpu6050_Data_t;

extern QueueHandle_t g_sensor_queue;

void vI2cSensorTask(void *pvParameters);
HAL_StatusTypeDef MPU6050_Init(I2C_HandleTypeDef *hi2c);
HAL_StatusTypeDef MPU6050_ReadAll(I2C_HandleTypeDef *hi2c,
                                  Mpu6050_Data_t *data);

#endif /* I2C_SENSOR_H */
```

### 实现文件（i2c_sensor.c）

```c
#include "i2c_sensor.h"
#include "string.h"

static const uint8_t MPU6050_WHO_AM_I = 0x75;
static const uint8_t MPU6050_PWR_MGMT_1 = 0x6B;

static uint8_t g_i2c_tx_buffer[2];
static uint8_t g_i2c_rx_buffer[14];

QueueHandle_t g_sensor_queue;

HAL_StatusTypeDef MPU6050_Init(I2C_HandleTypeDef *hi2c)
{
    /* 唤醒传感器 */
    g_i2c_tx_buffer[0] = MPU6050_PWR_MGMT_1;
    g_i2c_tx_buffer[1] = 0x00;
    return HAL_I2C_Master_Transmit(hi2c, I2C_SENSOR_ADDR << 1,
                                   g_i2c_tx_buffer, 2, 100);
}

HAL_StatusTypeDef MPU6050_ReadAll(I2C_HandleTypeDef *hi2c,
                                  Mpu6050_Data_t *data)
{
    HAL_StatusTypeDef status;

    /* 发送寄存器地址 */
    g_i2c_tx_buffer[0] = 0x3B;  /* ACCEL_XOUT_H */
    status = HAL_I2C_Master_Transmit(hi2c, I2C_SENSOR_ADDR << 1,
                                     g_i2c_tx_buffer, 1, 100);
    if (status != HAL_OK) return status;

    /* 读取 14 字节数据 */
    status = HAL_I2C_Master_Receive(hi2c, I2C_SENSOR_ADDR << 1,
                                    g_i2c_rx_buffer, 14, 100);
    if (status != HAL_OK) return status;

    /* 解析数据 */
    data->acc_x = (g_i2c_rx_buffer[0] << 8) | g_i2c_rx_buffer[1];
    data->acc_y = (g_i2c_rx_buffer[2] << 8) | g_i2c_rx_buffer[3];
    data->acc_z = (g_i2c_rx_buffer[4] << 8) | g_i2c_rx_buffer[5];
    data->gyro_x = (g_i2c_rx_buffer[8] << 8) | g_i2c_rx_buffer[9];
    data->gyro_y = (g_i2c_rx_buffer[10] << 8) | g_i2c_rx_buffer[11];
    data->gyro_z = (g_i2c_rx_buffer[12] << 8) | g_i2c_rx_buffer[13];

    return HAL_OK;
}

void vI2cSensorTask(void *pvParameters)
{
    Mpu6050_Data_t sensor_data;
    I2C_HandleTypeDef *hi2c1 = (I2C_HandleTypeDef *)pvParameters;

    /* 初始化传感器 */
    while (MPU6050_Init(hi2c1) != HAL_OK)
    {
        printf("MPU6050 初始化失败，重试中...\r\n");
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
    printf("MPU6050 初始化成功\r\n");

    while (1)
    {
        /* 读取传感器数据 */
        if (MPU6050_ReadAll(hi2c1, &sensor_data) == HAL_OK)
        {
            /* 发送到队列 */
            xQueueSend(g_sensor_queue, &sensor_data, 0);
        }
        else
        {
            printf("I2C 读取失败\r\n");
        }

        vTaskDelay(pdMS_TO_TICKS(20));  /* 50Hz 采样 */
    }
}
```

---

## TIM 定时器 + 任务触发

### 头文件（tim_trigger.h）

```c
#ifndef TIM_TRIGGER_H
#define TIM_TRIGGER_H

#include "main.h"
#include "FreeRTOS.h"
#include "task.h"

extern TaskHandle_t g_tim_task_handle;

void MX_TIM6_Init(void);
void vTimTriggerTask(void *pvParameters);

#endif /* TIM_TRIGGER_H */
```

### 实现文件（tim_trigger.c）

```c
#include "tim_trigger.h"
#include "dma.h"

TaskHandle_t g_tim_task_handle;

void MX_TIM6_Init(void)
{
    TIM_MasterConfigTypeDef sMasterConfig = {0};

    /* 配置 TIM6 作为系统节拍替代 */
    htim6.Instance = TIM6;
    htim6.Init.Prescaler = 83;      /* 84MHz / 84 = 1MHz */
    htim6.Init.Period = 1000 - 1;   /* 1ms 中断 */
    htim6.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim6.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;

    HAL_TIM_Base_MspInit(&htim6);
    HAL_TIM_Base_Init(&htim6);

    sMasterConfig.MasterOutputTrigger = TIM_TRGO_UPDATE;
    sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;

    HAL_TIMEx_MasterConfigSynchronization(&htim6, &sMasterConfig);

    /* 使能更新中断 */
    HAL_TIM_Base_Start_IT(&htim6);
}

void TIM6_DAC_IRQHandler(void)
{
    HAL_TIM_IRQHandler(&htim6);
}

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM6)
    {
        /* 发送任务通知（替代 systick） */
        BaseType_t xHigherPriorityTaskWoken = pdFALSE;
        vTaskNotifyGiveFromISR(g_tim_task_handle,
                               &xHigherPriorityTaskWoken);
        portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
    }
}

void vTimTriggerTask(void *pvParameters)
{
    uint32_t tick_count = 0;

    while (1)
    {
        /* 等待定时器通知 */
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        /* 执行周期任务 */
        tick_count++;
        if ((tick_count % 1000) == 0)
        {
            printf("运行时间: %lu ms\r\n", tick_count);
        }
    }
}
```
