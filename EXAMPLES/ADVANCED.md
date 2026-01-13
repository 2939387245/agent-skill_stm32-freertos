# 高级应用

本文档包含多任务传感器融合、Tickless 低功耗模式、STM32CubeMX 配置等高级应用示例。

---

## 3.1 多任务传感器融合

### 系统架构

```
+-------------------+     +-------------------+
|   传感器采集任务   | --> |   数据处理任务    |
|  (I2C 传感器)     |     |  (滤波、融合)     |
+-------------------+     +-------------------+
                                   |
                                   v
                          +-------------------+
                          |   数据发送任务    |
                          |  (UART/BLE/USB)   |
                          +-------------------+
```

### 实现代码

```c
#include "main.h"
#include "FreeRTOS.h"
#include "queue.h"
#include "semphr.h"

#define QUEUE_SIZE 20

/* 数据类型定义 */
typedef struct {
    float acc_x, acc_y, acc_z;
    float gyro_x, gyro_y, gyro_z;
    uint32_t timestamp;
} SensorData_t;

typedef struct {
    float roll, pitch, yaw;
    uint32_t timestamp;
} FusionData_t;

/* 通信机制 */
QueueHandle_t g_sensor_queue;      /* 原始数据队列 */
QueueHandle_t g_fusion_queue;      /* 融合数据队列 */
SemaphoreHandle_t g_i2c_mutex;     /* I2C 互斥锁 */

/* 传感器采集任务 */
void vSensorCollectTask(void *pvParameters)
{
    SensorData_t data;
    I2C_HandleTypeDef *hi2c = (I2C_HandleTypeDef *)pvParameters;

    while (1)
    {
        /* 获取 I2C 互斥锁 */
        if (xSemaphoreTake(g_i2c_mutex, pdMS_TO_TICKS(100)) == pdTRUE)
        {
            /* 读取传感器（MPU6050 简化版） */
            if (MPU6050_ReadAll(hi2c, &data) == HAL_OK)
            {
                data.timestamp = HAL_GetTick();
                xQueueSend(g_sensor_queue, &data, 0);
            }

            xSemaphoreGive(g_i2c_mutex);
        }

        vTaskDelay(pdMS_TO_TICKS(10));  /* 100Hz 采样 */
    }
}

/* 数据处理任务（互补滤波） */
void vDataProcessTask(void *pvParameters)
{
    SensorData_t raw_data;
    FusionData_t fused_data;
    static float gyro_x = 0, gyro_y = 0;
    static float acc_roll = 0, acc_pitch = 0;

    const float alpha = 0.98f;  /* 互补滤波系数 */

    while (1)
    {
        /* 接收原始数据 */
        if (xQueueReceive(g_sensor_queue, &raw_data, portMAX_DELAY) == pdTRUE)
        {
            /* 加速度计角度计算 */
            acc_roll = atan2(raw_data.acc_y, raw_data.acc_z) * 180.0f / 3.14159f;
            acc_pitch = atan2(-raw_data.acc_x, raw_data.acc_z) * 180.0f / 3.14159f;

            /* 互补滤波 */
            gyro_x += raw_data.gyro_x * 0.01f;
            gyro_y += raw_data.gyro_y * 0.01f;

            fused_data.roll = alpha * gyro_x + (1 - alpha) * acc_roll;
            fused_data.pitch = alpha * gyro_y + (1 - alpha) * acc_pitch;
            fused_data.yaw += raw_data.gyro_z * 0.01f;
            fused_data.timestamp = raw_data.timestamp;

            /* 发送到融合队列 */
            xQueueSend(g_fusion_queue, &fused_data, 0);
        }
    }
}

/* 数据发送任务 */
void vDataSendTask(void *pvParameters)
{
    FusionData_t fused_data;
    UART_HandleTypeDef *huart = (UART_HandleTypeDef *)pvParameters;

    while (1)
    {
        if (xQueueReceive(g_fusion_queue, &fused_data, portMAX_DELAY) == pdTRUE)
        {
            /* 格式化输出 */
            printf("Roll: %.2f, Pitch: %.2f, Yaw: %.2f\r\n",
                   fused_data.roll, fused_data.pitch, fused_data.yaw);
        }
    }
}

/* 主函数 */
int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_I2C1_Init();
    MX_UART1_Init();

    /* 创建通信机制 */
    g_sensor_queue = xQueueCreate(QUEUE_SIZE, sizeof(SensorData_t));
    g_fusion_queue = xQueueCreate(QUEUE_SIZE, sizeof(FusionData_t));
    g_i2c_mutex = xSemaphoreCreateMutex();

    if (g_sensor_queue && g_fusion_queue && g_i2c_mutex)
    {
        /* 创建任务 */
        xTaskCreate(vSensorCollectTask, "SensorCollect", 256,
                    &hi2c1, 3, NULL);
        xTaskCreate(vDataProcessTask, "DataProcess", 256,
                    NULL, 2, NULL);
        xTaskCreate(vDataSendTask, "DataSend", 128,
                    &huart1, 1, NULL);

        vTaskStartScheduler();
    }

    while (1);
}
```

---

## 3.2 Tickless 低功耗模式

### 配置步骤

#### 1. FreeRTOSConfig.h 配置

```c
/* FreeRTOSConfig.h */
#define configUSE_TICKLESS_IDLE    2       /* 启用 Tickless */
#define configPRE_SLEEP_PROCESSING(x) vPreSleepProcessing(x)
#define configPOST_SLEEP_PROCESSING(x) vPostSleepProcessing(x)

/* 外部声明 */
extern void vPreSleepProcessing(uint32_t *expected_idle_time);
extern void vPostSleepProcessing(uint32_t *expected_idle_time);
```

#### 2. Tickless 实现代码

```c
#include "main.h"
#include "FreeRTOS.h"

/* 低功耗模式配置 */
#define STOP_MODE_TIMEOUT pdMS_TO_TICKS(100)  /* STOP 模式超时 */

/* 进入低功耗前的处理 */
void vPreSleepProcessing(uint32_t *expected_idle_time)
{
    /* 降低时钟频率 */
    if (*expected_idle_time > STOP_MODE_TIMEOUT)
    {
        /* 配置为 STOP 模式 */
        /* 此处根据具体芯片配置 */
        __HAL_RCC_PWR_CLK_ENABLE();

        /* 降低主频 */
        __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE2);
    }
}

/* 退出低功耗后的处理 */
void vPostSleepProcessing(uint32_t *expected_idle_time)
{
    (void)expected_idle_time;

    /* 恢复时钟频率 */
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    /* 重新配置时钟 */
    SystemClock_Config();
}

/* 空闲任务钩子（FreeRTOS 自动调用） */
void vApplicationIdleHook(void)
{
    /* 可以在此处进入最低功耗模式 */
    __WFI();  /* Wait For Interrupt */
}
```

#### 3. STOP 模式实现

```c
#include "stm32l4xx_hal_pwr.h"
#include "stm32l4xx_ll_pwr.h"

void vEnterStopMode(uint32_t timeout_ms)
{
    /* 保存当前时钟 */
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    HAL_RCC_OscConfig(&RCC_OscInitStruct);

    /* 清除唤醒标志 */
    __HAL_PWR_CLEAR_FLAG(PWR_FLAG_WU);

    /* 进入 STOP 模式 */
    HAL_PWR_EnterSTOPMode(PWR_LOWPOWERREGULATOR_ON,
                          PWR_STOPENTRY_WFI);
}

void vStopModeTask(void *pvParameters)
{
    while (1)
    {
        /* 正常模式运行 */
        vTaskDelay(pdMS_TO_TICKS(100));

        /* 进入低功耗模式 */
        printf("进入 STOP 模式\r\n");

        /* 此处应使用 vPortSuppressTicksAndSleep() */
        /* 实际使用 FreeRTOS 自动处理 */

        printf("退出 STOP 模式\r\n");
    }
}
```

---

## 3.3 STM32CubeMX 配置说明

### FreeRTOS 中间件配置

```
STM32CubeMX → Middleware → FreeRTOS

Config Parameters:
├── VERSION: V10 (or CMSIS-R2)
├── TOTAL_HEAP_SIZE: 3072 (bytes)
├── USE_IDLE_HOOK: ✓
├── USE_TICK_HOOK: ✗
├── USE_MUTEXES: ✓
├── USE_RECURSIVE_MUTEXES: ✓
├── USE_COUNTING_SEMAPHORES: ✓
├── USE_TASK_NOTIFICATIONS: ✓
├── ENFORCE_SYSTEM_VIEWER: ✗ (默认)
└── CHECK_FOR_STACK_OVERFLOW: 2 (Method 2)
```

### NVIC 配置

```
STM32CubeMX → Configuration → NVIC

┌─────────────────────────────────────────────────────────────┐
│ NVIC                                               [x]     │
├─────────────────────────────────────────────────────────────┤
│ NVIC_Priority_Group: NVIC_PRIORITYGROUP_4                 │
├─────────────────────────────────────────────────────────────┤
│ 优先级表:                                                   │
│                                                             │
│  System          │ 优先级 │ 子优先级 │ 抢占使能 │          │
│ ─────────────────┼────────┼──────────┼──────────┤          │
│  NonMaskableInt  │   0    │    0     │    -     │          │
│  HardFault       │   0    │    0     │    -     │          │
│  MemoryManagement│   0    │    0     │    -     │          │
│  BusFault        │   0    │    0     │    -     │          │
│  UsageFault      │   0    │    0     │    -     │          │
│  SVCall          │   0    │    0     │    -     │          │
│  DebugMonitor    │   0    │    0     │    -     │          │
│  PendSV          │  15    │    0     │    -     │  FreeRTOS│
│  SysTick         │  15    │    0     │    -     │  FreeRTOS│
│  USART1         │   5    │    0     │    ✓     │  外设    │
│  DMA1_Channel1  │   6    │    0     │    ✓     │  外设    │
│  ...           │  ...   │   ...    │   ...    │  ...     │
└─────────────────────────────────────────────────────────────┘

关键点：
1. PendSV 和 SysTick 必须设为最低优先级（15）
2. FreeRTOS 内核中断优先级为 5（configKERNEL_INTERRUPT_PRIORITY）
3. 外设中断优先级应高于内核（5-15）
```

### 外设 + DMA 配置

```
UART1 配置:
├── Mode: Asynchronous
├── Baud Rate: 115200
├── Data Bits: 8
├── Parity: None
├── Stop Bits: 1
├── DMA Settings: ✓
│   ├── USART1_TX: DMA1 Channel 4
│   └── USART1_RX: DMA1 Channel 5
└── NVIC Settings:
    ├── USART1 global interrupt: ✓ (Priority 5)
    └── DMA1 channel global interrupt: ✓ (Priority 6)

ADC1 配置:
├── Mode: Scan Continuous Conversion
├── Enable Regular Conversions: ✓
├── Number of Conversion: 3
├── DMA Continuos Requests: ✓
├── DMA Settings: ✓
│   └── ADC1: DMA1 Channel 1
└── NVIC Settings:
    └── DMA1 channel 1/2/3 interrupt: ✓ (Priority 6)
```

### 生成的代码修改

```c
/* 生成的 main.c 需要修改 */

/* 1. HAL 初始化放在 FreeRTOS 之前 */
int main(void)
{
    HAL_Init();
    SystemClock_Config();

    /* MX 初始化（不包含 FreeRTOS） */
    MX_GPIO_Init();
    MX_DMA_Init();
    MX_USART1_UART_Init();

    /* 创建任务 */
    StartDefaultTask();
    vTaskStartScheduler();  /* 在此处启动调度器 */
}

/* 2. 删除默认生成的 MX_FREERTOS_Init() */

/* 3. 任务函数放在 main 之前或独立文件 */

/* 4. 任务堆栈大小根据需求调整 */
```
