# FreeRTOS API 参考

本文档包含 FreeRTOS 原生 API 和 CMSIS-RTOS v2 API 的完整参考。

---

## 1.1 原生 FreeRTOS API（v10+）

### 任务管理

```c
/* 动态任务创建 */
BaseType_t xTaskCreate(
    TaskFunction_t pxTaskCode,      // 任务函数指针
    const char * const pcName,      // 任务名称
    const uint16_t usStackDepth,    // 堆栈深度（字为单位）
    void * const pvParameters,      // 传递给任务的参数
    UBaseType_t uxPriority,         // 任务优先级
    TaskHandle_t * const pxCreatedTask  // 任务句柄（输出）
);

/* 静态任务创建（自行分配内存） */
TaskHandle_t xTaskCreateStatic(
    TaskFunction_t pxTaskCode,
    const char * const pcName,
    uint32_t ulStackDepth,
    void * const pvParameters,
    UBaseType_t uxPriority,
    StackType_t * const pxStackBuffer,
    StaticTask_t * const pxTaskBuffer
);

/* 任务删除 */
void vTaskDelete(TaskHandle_t xTask);

/* 任务延时 */
void vTaskDelay(const TickType_t xTicksToDelay);           // 相对延时
void vTaskDelayUntil(TickType_t *pxPreviousWakeTime,      // 绝对延时
                     const TickType_t xTimeIncrement);

/* 任务优先级 */
void vTaskPrioritySet(TaskHandle_t xTask, UBaseType_t uxNewPriority);
UBaseType_t uxTaskPriorityGet(TaskHandle_t xTask);

/* 堆栈溢出检测 */
UBaseType_t uxTaskGetStackHighWaterMark(TaskHandle_t xTask);
```

### 队列（Queue）

```c
/* 创建队列 */
QueueHandle_t xQueueCreate(UBaseType_t uxQueueLength,   // 队列长度
                           UBaseType_t uxItemSize);    // 单个元素大小

/* 发送数据（任务中） */
BaseType_t xQueueSend(QueueHandle_t xQueue,
                      const void *pvItemToQueue,
                      TickType_t xTicksToWait);

/* 接收数据（任务中） */
BaseType_t xQueueReceive(QueueHandle_t xQueue,
                         void *pvBuffer,
                         TickType_t xTicksToWait);

/* ISR 中发送（带优先级继承） */
BaseType_t xQueueSendFromISR(QueueHandle_t xQueue,
                             const void *pvItemToQueue,
                             BaseType_t *pxHigherPriorityTaskWoken);

/* ISR 中接收 */
BaseType_t xQueueReceiveFromISR(QueueHandle_t xQueue,
                                void *pvBuffer,
                                BaseType_t *pxHigherPriorityTaskWoken);
```

### 信号量（Semaphore）

```c
/* 创建二值信号量 */
SemaphoreHandle_t xSemaphoreCreateBinary(void);

/* 创建计数信号量 */
SemaphoreHandle_t xSemaphoreCreateCounting(UBaseType_t uxMaxCount,
                                           UBaseType_t uxInitialCount);

/* 创建互斥锁（带优先级继承） */
SemaphoreHandle_t xSemaphoreCreateMutex(void);

/* 创建递归互斥锁 */
SemaphoreHandle_t xSemaphoreCreateRecursiveMutex(void);

/* 获取信号量 */
BaseType_t xSemaphoreTake(SemaphoreHandle_t xSemaphore,
                          TickType_t xTicksToWait);

/* 释放信号量 */
BaseType_t xSemaphoreGive(SemaphoreHandle_t xSemaphore);

/* ISR 中释放 */
BaseType_t xSemaphoreGiveFromISR(SemaphoreHandle_t xSemaphore,
                                 BaseType_t *pxHigherPriorityTaskWoken);
```

### 事件组（Event Groups）

```c
/* 创建事件组 */
EventGroupHandle_t xEventGroupCreate(void);

/* 设置事件位 */
EventBits_t xEventGroupSetBits(EventGroupHandle_t xEventGroup,
                               const EventBits_t uxBitsToSet);

/* 清除事件位 */
EventBits_t xEventGroupClearBits(EventGroupHandle_t xEventGroup,
                                 const EventBits_t uxBitsToClear);

/* 等待事件位（AND/OR 逻辑） */
EventBits_t xEventGroupWaitBits(const EventGroupHandle_t xEventGroup,
                                const EventBits_t uxBitsToWaitFor,
                                const BaseType_t xClearOnExit,
                                const BaseType_t xWaitForAllBits,
                                TickType_t xTicksToWait);

/* ISR 中设置事件位 */
BaseType_t xEventGroupSetBitsFromISR(EventGroupHandle_t xEventGroup,
                                     const EventBits_t uxBitsToSet,
                                     BaseType_t *pxHigherPriorityTaskWoken);
```

### 任务通知（Task Notifications）

```c
/* 发送通知（直接唤醒任务） */
BaseType_t xTaskNotify(TaskHandle_t xTaskToNotify,
                       uint32_t ulValue,
                       eNotifyAction eAction);

/* 发送通知（ISR 版本） */
BaseType_t xTaskNotifyFromISR(TaskHandle_t xTaskToNotify,
                              uint32_t ulValue,
                              eNotifyAction eAction,
                              BaseType_t *pxHigherPriorityTaskWoken);

/* 接收通知 */
BaseType_t xTaskNotifyWait(uint32_t ulBitsToClearOnEntry,
                           uint32_t ulBitsToClearOnExit,
                           uint32_t *pulNotificationValue,
                           TickType_t xTicksToWait);
```

---

## 1.2 CMSIS-RTOS v2 API 映射

### 线程（Task）

```c
/* 创建线程 */
osThreadId_t osThreadNew(osThreadFunc_t func, void *arg,
                         const osThreadAttr_t *attr);

/* 线程延时 */
osStatus_t osDelay(uint32_t ticks);
osStatus_t osDelayUntil(uint32_t *ticks, uint32_t period);

/* 线程终止 */
osStatus_t osThreadTerminate(osThreadId_t thread_id);

/* 线程退出 */
void osThreadExit(void);
```

### 队列（Queue）

```c
/* 创建队列 */
osMessageQueueId_t osMessageQueueNew(uint32_t msg_count,
                                     uint32_t msg_size,
                                     const osMessageQueueAttr_t *attr);

/* 发送消息 */
osStatus_t osMessageQueuePut(osMessageQueueId_t mq_id,
                             const void *msg_ptr,
                             uint8_t msg_prio,
                             uint32_t timeout);

/* 接收消息 */
osStatus_t osMessageQueueGet(osMessageQueueId_t mq_id,
                             void *msg_ptr,
                             uint8_t *msg_prio,
                             uint32_t timeout);
```

### 信号量（Semaphore）

```c
/* 创建信号量 */
osSemaphoreId_t osSemaphoreNew(uint32_t max_count,
                               uint32_t initial_count,
                               const osSemaphoreAttr_t *attr);

/* 获取信号量 */
osStatus_t osSemaphoreAcquire(osSemaphoreId_t semaphore_id,
                               uint32_t timeout);

/* 释放信号量 */
osStatus_t osSemaphoreRelease(osSemaphoreId_t semaphore_id);
```

### 互斥锁（Mutex）

```c
/* 创建互斥锁 */
osMutexId_t osMutexNew(const osMutexAttr_t *attr);

/* 获取互斥锁 */
osStatus_t osMutexAcquire(osMutexId_t mutex_id, uint32_t timeout);

/* 释放互斥锁 */
osStatus_t osMutexRelease(osMutexId_t mutex_id);
```

### 事件（Event）

```c
/* 创建事件 */
osEventFlagsId_t osEventFlagsNew(const osEventFlagsAttr_t *attr);

/* 设置事件 */
uint32_t osEventFlagsSet(osEventFlagsId_t ef_id, uint32_t flags);

/* 清除事件 */
uint32_t osEventFlagsClear(osEventFlagsId_t ef_id, uint32_t flags);

/* 等待事件 */
uint32_t osEventFlagsWait(osEventFlagsId_t ef_id,
                          uint32_t flags,
                          uint32_t options,
                          uint32_t timeout);
```

---

## 内存优化

### 静态分配 vs 动态分配

```c
/* 静态任务控制块和堆栈 */
StaticTask_t xTask1_TCB;
StackType_t xTask1_Stack[128];  /* 128 * 4 = 512 字节 */

/* 静态队列控制块 */
typedef struct {
    uint8_t buffer[10][32];  /* 10 个元素，每个 32 字节 */
    StaticQueue_t queue;
} StaticQueue_t;

void vCreateStaticObjects(void)
{
    /* 创建静态任务 */
    xTaskCreateStatic(vTaskFunction, "StaticTask1",
                      128, NULL, osPriorityNormal,
                      xTask1_Stack, &xTask1_TCB);

    /* 创建静态队列 */
    QueueHandle_t queue = xQueueCreateStatic(10, 32,
                                             g_queue_buffer,
                                             &g_queue_cb);
}
```

### 堆栈估算方法

```c
void vTaskMonitorStack(TaskHandle_t xTask)
{
    UBaseType_t high_water_mark;

    if (xTask == NULL)
    {
        high_water_mark = uxTaskGetStackHighWaterMark(NULL);
    }
    else
    {
        high_water_mark = uxTaskGetStackHighWaterMark(xTask);
    }

    printf("堆栈剩余: %lu 字 (%lu 字节)\r\n",
           high_water_mark, high_water_mark * 4);

    if (high_water_mark < 20)
    {
        printf("警告: 堆栈即将耗尽！\r\n");
    }
}
```

### 堆栈溢出配置

```c
/* FreeRTOSConfig.h */
#define configCHECK_FOR_STACK_OVERFLOW 2  /* 方法 2 */

void vApplicationStackOverflowHook(TaskHandle_t xTask,
                                   char *pcTaskName)
{
    printf("堆栈溢出: %s\r\n", pcTaskName);
    while (1);
}
```

### heap 碎片避免

```c
#define MEMPOOL_ITEM_SIZE 64
#define MEMPOOL_ITEMS 20

typedef struct {
    uint8_t data[MEMPOOL_ITEM_SIZE];
} MemPoolItem_t;

typedef struct {
    MemPoolItem_t items[MEMPOOL_ITEMS];
    uint8_t used[MEMPOOL_ITEMS];
} MemPool_t;

void *pvMemPoolAlloc(MemPool_t *pool)
{
    for (int i = 0; i < MEMPOOL_ITEMS; i++)
    {
        if (pool->used[i] == 0)
        {
            pool->used[i] = 1;
            memset(pool->items[i].data, 0, MEMPOOL_ITEM_SIZE);
            return pool->items[i].data;
        }
    }
    return NULL;
}

void vMemPoolFree(MemPool_t *pool, void *p)
{
    for (int i = 0; i < MEMPOOL_ITEMS; i++)
    {
        if (pool->items[i].data == p)
        {
            pool->used[i] = 0;
            break;
        }
    }
}
```
