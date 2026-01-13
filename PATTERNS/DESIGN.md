# 设计模式

本文档介绍生产者-消费者、发布-订阅、状态机、资源池等设计模式的实现方法。

---

## 1.1 生产者-消费者（Producer-Consumer）

### 模式说明

生产者-消费者模式是嵌入式系统中最常用的模式之一，适用于：
- 数据采集与处理分离
- 传感器数据缓冲
- 串口数据接收与解析

### 实现架构

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  生产者任务  │ ---> │    队列     │ ---> │  消费者任务  │
│  采集数据   │      │  缓冲数据   │      │  处理数据   │
└─────────────┘      └─────────────┘      └─────────────┘
```

### 完整实现

```c
#include "main.h"
#include "FreeRTOS.h"
#include "queue.h"
#include "semphr.h"

#define QUEUE_LENGTH 20
#define QUEUE_ITEM_SIZE sizeof(uint32_t)

typedef struct {
    uint32_t sensor_id;
    uint32_t value;
    uint32_t timestamp;
} SensorMessage_t;

/* 队列和信号量 */
QueueHandle_t g_sensor_queue;
SemaphoreHandle_t g_data_ready_sem;

/* 生产者任务：模拟传感器采集 */
void vSensorTask(void *pvParameters)
{
    SensorMessage_t msg;
    uint32_t count = 0;

    while (1)
    {
        /* 采集传感器数据 */
        msg.sensor_id = 1;
        msg.value = HAL_ADC_GetValue(&hadc1);  /* 假设已配置 ADC */
        msg.timestamp = HAL_GetTick();

        /* 发送数据到队列 */
        if (xQueueSend(g_sensor_queue, &msg, 0) == pdTRUE)
        {
            /* 发送数据就绪信号 */
            xSemaphoreGive(g_data_ready_sem);
        }

        count++;
        vTaskDelay(pdMS_TO_TICKS(100));  /* 10Hz 采样 */
    }
}

/* 消费者任务：处理数据 */
void vProcessTask(void *pvParameters)
{
    SensorMessage_t msg;

    while (1)
    {
        /* 等待数据就绪信号 */
        if (xSemaphoreTake(g_data_ready_sem, portMAX_DELAY) == pdTRUE)
        {
            /* 从队列获取数据 */
            while (xQueueReceive(g_sensor_queue, &msg, 0) == pdTRUE)
            {
                /* 处理数据 */
                printf("传感器 #%lu: %lu (时间: %lu)\r\n",
                       msg.sensor_id, msg.value, msg.timestamp);
            }
        }
    }
}

void vProducerConsumerDemo(void)
{
    /* 创建队列 */
    g_sensor_queue = xQueueCreate(QUEUE_LENGTH, QUEUE_ITEM_SIZE);

    /* 创建二值信号量 */
    g_data_ready_sem = xSemaphoreCreateBinary();

    /* 创建任务 */
    xTaskCreate(vSensorTask, "Sensor", 128, NULL, 2, NULL);
    xTaskCreate(vProcessTask, "Process", 128, NULL, 2, NULL);
}
```

### 变体：多生产者-多消费者

```c
/* 多个生产者共享队列 */
void vSensorTask1(void *pvParameters)
{
    SensorMessage_t msg;
    msg.sensor_id = 1;
    while (1) {
        msg.value = read_sensor1();
        xQueueSend(g_sensor_queue, &msg, 0);
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

void vSensorTask2(void *pvParameters)
{
    SensorMessage_t msg;
    msg.sensor_id = 2;
    while (1) {
        msg.value = read_sensor2();
        xQueueSend(g_sensor_queue, &msg, 0);
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

/* 消费者通过 sensor_id 区分数据源 */
void vProcessTaskMulti(void *pvParameters)
{
    SensorMessage_t msg;
    while (1) {
        xQueueReceive(g_sensor_queue, &msg, portMAX_DELAY);

        switch (msg.sensor_id) {
            case 1:
                process_sensor1_data(msg.value);
                break;
            case 2:
                process_sensor2_data(msg.value);
                break;
        }
    }
}
```

---

## 1.2 发布-订阅（Publish-Subscribe）

### 模式说明

发布-订阅模式使用事件组实现，适用于：
- 多条件触发
- 广播通知
- 状态机事件

### 实现代码

```c
#include "main.h"
#include "FreeRTOS.h"
#include "event_groups.h"

/* 事件位定义 */
#define EVENT_BUTTON_PRESS   (1 << 0)
#define EVENT_SENSOR_ALARM   (1 << 1)
#define EVENT_TIMEOUT        (1 << 2)
#define EVENT_ALL            (EVENT_BUTTON_PRESS | EVENT_SENSOR_ALARM | EVENT_TIMEOUT)

/* 事件组 */
EventGroupHandle_t g_event_group;

/* 订阅者任务 */
void vAlarmTask(void *pvParameters)
{
    EventBits_t bits;

    while (1)
    {
        /* 订阅所有事件 */
        bits = xEventGroupWaitBits(g_event_group,
                                   EVENT_ALL,
                                   pdTRUE,   /* 清除位 */
                                   pdFALSE,  /* 任一事件（OR） */
                                   portMAX_DELAY);

        if (bits & EVENT_BUTTON_PRESS)
        {
            printf("报警任务：收到按钮事件\r\n");
        }

        if (bits & EVENT_SENSOR_ALARM)
        {
            printf("报警任务：收到传感器报警\r\n");
            /* 触发报警动作 */
        }
    }
}

/* 发布者任务 */
void vButtonTask(void *pvParameters)
{
    while (1)
    {
        if (HAL_GPIO_ReadPin(BUTTON_GPIO_Port, BUTTON_Pin) == GPIO_PIN_RESET)
        {
            /* 延时消抖 */
            vTaskDelay(pdMS_TO_TICKS(50));
            if (HAL_GPIO_ReadPin(BUTTON_GPIO_Port, BUTTON_Pin) == GPIO_PIN_RESET)
            {
                /* 发布按钮事件 */
                xEventGroupSetBits(g_event_group, EVENT_BUTTON_PRESS);
                printf("按钮任务：发布按钮事件\r\n");
            }

            /* 等待释放 */
            while (HAL_GPIO_ReadPin(BUTTON_GPIO_Port, BUTTON_Pin) == GPIO_PIN_RESET)
            {
                vTaskDelay(pdMS_TO_TICKS(10));
            }
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

void vPublishSubscribeDemo(void)
{
    g_event_group = xEventGroupCreate();

    xTaskCreate(vAlarmTask, "Alarm", 128, NULL, 2, NULL);
    xTaskCreate(vButtonTask, "Button", 128, NULL, 2, NULL);
}
```

---

## 1.3 状态机（State Machine）

### 模式说明

状态机模式适用于：
- 协议解析
- 业务流程控制
- 模式切换

### 实现代码

```c
#include "main.h"
#include "FreeRTOS.h"

/* 状态机状态定义 */
typedef enum {
    STATE_IDLE = 0,
    STATE_INIT,
    STATE_CONNECTING,
    STATE_CONNECTED,
    STATE_DISCONNECTED,
    STATE_ERROR
} AppState_t;

/* 事件定义 */
typedef enum {
    EVENT_NONE = 0,
    EVENT_START,
    EVENT_CONNECT,
    EVENT_DISCONNECT,
    EVENT_TIMEOUT,
    EVENT_ERROR
} AppEvent_t;

/* 状态机控制块 */
typedef struct {
    AppState_t current_state;
    AppState_t next_state;
    AppEvent_t pending_event;
    TickType_t last_state_time;
} StateMachine_t;

/* 状态机实例 */
static StateMachine_t g_sm;

/* 状态处理函数 */
static void handle_idle(AppEvent_t event)
{
    switch (event) {
        case EVENT_START:
            printf("状态机：从 IDLE 切换到 INIT\r\n");
            g_sm.next_state = STATE_INIT;
            break;
        default:
            break;
    }
}

static void handle_init(AppEvent_t event)
{
    switch (event) {
        case EVENT_CONNECT:
            printf("状态机：初始化完成，开始连接\r\n");
            g_sm.next_state = STATE_CONNECTING;
            break;
        case EVENT_ERROR:
            printf("状态机：初始化失败，进入错误状态\r\n");
            g_sm.next_state = STATE_ERROR;
            break;
        default:
            break;
    }
}

static void handle_connecting(AppEvent_t event)
{
    switch (event) {
        case EVENT_TIMEOUT:
            printf("状态机：连接超时，重试\r\n");
            /* 重连逻辑 */
            g_sm.next_state = STATE_CONNECTING;
            break;
        case EVENT_CONNECT:
            printf("状态机：连接成功\r\n");
            g_sm.next_state = STATE_CONNECTED;
            break;
        default:
            break;
    }
}

static void handle_connected(AppEvent_t event)
{
    switch (event) {
        case EVENT_DISCONNECT:
            printf("状态机：断开连接\r\n");
            g_sm.next_state = STATE_DISCONNECTED;
            break;
        case EVENT_ERROR:
            printf("状态机：连接错误\r\n");
            g_sm.next_state = STATE_ERROR;
            break;
        default:
            break;
    }
}

/* 状态机处理函数 */
void vStateMachineTask(void *pvParameters)
{
    /* 初始化状态机 */
    g_sm.current_state = STATE_IDLE;
    g_sm.next_state = STATE_IDLE;
    g_sm.pending_event = EVENT_NONE;

    while (1)
    {
        /* 处理当前状态 */
        switch (g_sm.current_state) {
            case STATE_IDLE:
                handle_idle(g_sm.pending_event);
                break;
            case STATE_INIT:
                handle_init(g_sm.pending_event);
                break;
            case STATE_CONNECTING:
                handle_connecting(g_sm.pending_event);
                break;
            case STATE_CONNECTED:
                handle_connected(g_sm.pending_event);
                break;
            default:
                break;
        }

        /* 状态转换 */
        if (g_sm.next_state != g_sm.current_state)
        {
            printf("状态机转换: %d -> %d\r\n",
                   g_sm.current_state, g_sm.next_state);
            g_sm.current_state = g_sm.next_state;
            g_sm.last_state_time = xTaskGetTickCount();
        }

        /* 清空事件 */
        g_sm.pending_event = EVENT_NONE;

        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

/* 事件发送接口 */
void StateMachine_SendEvent(AppEvent_t event)
{
    g_sm.pending_event = event;
}
```

---

## 1.4 资源池管理

### 模式说明

资源池模式适用于：
- 固定大小缓冲区管理
- 动态对象复用
- 内存碎片避免

### 实现代码

```c
#include "main.h"
#include "FreeRTOS.h"
#include "semphr.h"

#define BUFFER_POOL_SIZE 10
#define BUFFER_SIZE 128

/* 缓冲区项 */
typedef struct {
    uint8_t data[BUFFER_SIZE];
    uint32_t length;
    uint32_t timestamp;
} BufferItem_t;

/* 缓冲区池 */
typedef struct {
    BufferItem_t items[BUFFER_POOL_SIZE];
    uint8_t used[BUFFER_POOL_SIZE];
    SemaphoreHandle_t mutex;
    SemaphoreHandle_t free_count;
} BufferPool_t;

/* 全局缓冲区池 */
static BufferPool_t g_buffer_pool;

/* 初始化缓冲区池 */
void BufferPool_Init(void)
{
    memset(&g_buffer_pool, 0, sizeof(g_buffer_pool));
    g_buffer_pool.mutex = xSemaphoreCreateMutex();
    g_buffer_pool.free_count = xSemaphoreCreateCounting(BUFFER_POOL_SIZE,
                                                        BUFFER_POOL_SIZE);

    /* 初始时所有缓冲区都可用 */
    for (int i = 0; i < BUFFER_POOL_SIZE; i++)
    {
        xSemaphoreGive(g_buffer_pool.free_count);
    }
}

/* 从池中获取缓冲区 */
BufferItem_t *BufferPool_Alloc(void)
{
    BufferItem_t *item = NULL;

    /* 等待空闲缓冲区 */
    if (xSemaphoreTake(g_buffer_pool.free_count, pdMS_TO_TICKS(100)) == pdFALSE)
    {
        return NULL;  /* 超时，无可用缓冲区 */
    }

    /* 获取互斥锁 */
    if (xSemaphoreTake(g_buffer_pool.mutex, pdMS_TO_TICKS(50)) == pdFALSE)
    {
        /* 归还信号量 */
        xSemaphoreGive(g_buffer_pool.free_count);
        return NULL;
    }

    /* 查找空闲缓冲区 */
    for (int i = 0; i < BUFFER_POOL_SIZE; i++)
    {
        if (g_buffer_pool.used[i] == 0)
        {
            g_buffer_pool.used[i] = 1;
            item = &g_buffer_pool.items[i];
            break;
        }
    }

    xSemaphoreGive(g_buffer_pool.mutex);

    return item;
}

/* 归还缓冲区到池 */
void BufferPool_Free(BufferItem_t *item)
{
    if (item == NULL) return;

    xSemaphoreTake(g_buffer_pool.mutex, portMAX_DELAY);

    for (int i = 0; i < BUFFER_POOL_SIZE; i++)
    {
        if (&g_buffer_pool.items[i] == item)
        {
            g_buffer_pool.used[i] = 0;
            memset(item, 0, sizeof(BufferItem_t));
            break;
        }
    }

    xSemaphoreGive(g_buffer_pool.mutex);
    xSemaphoreGive(g_buffer_pool.free_count);
}

/* 获取池状态 */
void BufferPool_GetStats(uint32_t *total, uint32_t *used)
{
    xSemaphoreTake(g_buffer_pool.mutex, portMAX_DELAY);

    *total = BUFFER_POOL_SIZE;
    *used = 0;
    for (int i = 0; i < BUFFER_POOL_SIZE; i++)
    {
        if (g_buffer_pool.used[i]) (*used)++;
    }

    xSemaphoreGive(g_buffer_pool.mutex);
}

/* 使用示例 */
void vBufferPoolDemoTask(void *pvParameters)
{
    BufferItem_t *buf;
    uint32_t total, used;

    BufferPool_Init();

    while (1)
    {
        /* 分配缓冲区 */
        buf = BufferPool_Alloc();
        if (buf != NULL)
        {
            /* 使用缓冲区 */
            buf->length = sprintf((char *)buf->data,
                                  "消息 #%lu", HAL_GetTick());
            buf->timestamp = HAL_GetTick();

            printf("分配缓冲区 #%lu, 剩余: ", HAL_GetTick());
            BufferPool_GetStats(&total, &used);
            printf("%lu/%lu\r\n", total - used, total);

            /* 模拟处理 */
            vTaskDelay(pdMS_TO_TICKS(500));

            /* 归还缓冲区 */
            BufferPool_Free(buf);
        }
        else
        {
            printf("缓冲区池已满，等待...\r\n");
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }
}
```
