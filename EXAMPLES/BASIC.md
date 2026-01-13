# 基础示例

本文档包含 FreeRTOS 基础组件的完整示例代码。

---

## 1.1 动态任务创建

```c
#include "main.h"
#include "FreeRTOS.h"
#include "task.h"

/* 任务函数 */
void vTask1(void *pvParameters)
{
    while (1)
    {
        /* 任务代码 */
        HAL_GPIO_TogglePin(LED_GPIO_Port, LED_Pin);
        printf("Task1 运行\r\n");

        /* 延时 500ms */
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

void vTask2(void *pvParameters)
{
    while (1)
    {
        /* 任务代码 */
        HAL_GPIO_TogglePin(LED2_GPIO_Port, LED2_Pin);
        printf("Task2 运行\r\n");

        /* 延时 1000ms */
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();

    /* 创建任务 */
    BaseType_t ret1 = xTaskCreate(vTask1, "Task1",
                                  128,  /* 堆栈深度（字） */
                                  NULL, /* 参数 */
                                  2,    /* 优先级 */
                                  NULL);/* 句柄 */

    BaseType_t ret2 = xTaskCreate(vTask2, "Task2",
                                  128,
                                  NULL,
                                  2,
                                  NULL);

    if (ret1 == pdPASS && ret2 == pdPASS)
    {
        printf("任务创建成功，启动调度器\r\n");
        vTaskStartScheduler();
    }
    else
    {
        printf("任务创建失败\r\n");
    }

    while (1);
}
```

---

## 1.2 静态任务创建

```c
#include "main.h"
#include "FreeRTOS.h"
#include "task.h"

/* 静态任务控制块和堆栈（全局变量） */
static StaticTask_t xTask1_TCB;
static StackType_t xTask1_Stack[128];

static StaticTask_t xTask2_TCB;
static StackType_t xTask2_Stack[256];

/* 任务函数 */
void vTask1(void *pvParameters)
{
    while (1)
    {
        printf("静态任务1运行\r\n");
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void vTask2(void *pvParameters)
{
    while (1)
    {
        printf("静态任务2运行\r\n");
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();

    /* 创建静态任务 */
    TaskHandle_t handle1 = xTaskCreateStatic(vTask1, "Task1",
                                             128,  /* 堆栈深度（字） */
                                             NULL, /* 参数 */
                                             2,    /* 优先级 */
                                             xTask1_Stack,
                                             &xTask1_TCB);

    TaskHandle_t handle2 = xTaskCreateStatic(vTask2, "Task2",
                                             256,
                                             NULL,
                                             2,
                                             xTask2_Stack,
                                             &xTask2_TCB);

    if (handle1 != NULL && handle2 != NULL)
    {
        printf("静态任务创建成功，启动调度器\r\n");
        vTaskStartScheduler();
    }
    else
    {
        printf("静态任务创建失败\r\n");
    }

    while (1);
}
```

---

## 1.3 队列（生产者-消费者）

```c
#include "main.h"
#include "FreeRTOS.h"
#include "queue.h"

/* 数据帧定义 */
typedef struct {
    uint32_t id;
    float value;
    uint32_t timestamp;
} DataFrame_t;

/* 全局队列 */
QueueHandle_t g_data_queue;

/* 生产者任务 */
void vProducerTask(void *pvParameters)
{
    DataFrame_t frame;
    uint32_t count = 0;

    while (1)
    {
        /* 产生数据 */
        frame.id = count;
        frame.value = (float)(count * 0.1f);
        frame.timestamp = HAL_GetTick();

        /* 发送到队列 */
        if (xQueueSend(g_data_queue, &frame, 0) == pdTRUE)
        {
            printf("生产者: 发送数据 #%lu\r\n", count);
        }
        else
        {
            printf("生产者: 队列满，丢弃数据\r\n");
        }

        count++;
        vTaskDelay(pdMS_TO_TICKS(200));
    }
}

/* 消费者任务 */
void vConsumerTask(void *pvParameters)
{
    DataFrame_t frame;

    while (1)
    {
        /* 从队列接收数据（无限等待） */
        if (xQueueReceive(g_data_queue, &frame, portMAX_DELAY) == pdTRUE)
        {
            printf("消费者: 收到数据 #%lu, 值=%.2f, 时间=%lu\r\n",
                   frame.id, frame.value, frame.timestamp);
        }
    }
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();

    /* 创建队列：10 个元素，每个元素大小 sizeof(DataFrame_t) */
    g_data_queue = xQueueCreate(10, sizeof(DataFrame_t));

    if (g_data_queue != NULL)
    {
        /* 创建任务 */
        xTaskCreate(vProducerTask, "Producer", 128, NULL, 2, NULL);
        xTaskCreate(vConsumerTask, "Consumer", 128, NULL, 2, NULL);

        vTaskStartScheduler();
    }
    else
    {
        printf("队列创建失败\r\n");
    }

    while (1);
}
```

---

## 1.4 二值信号量（任务同步）

```c
#include "main.h"
#include "FreeRTOS.h"
#include "semphr.h"

/* 二值信号量 */
SemaphoreHandle_t g_button_sem;

/* 按钮中断回调 */
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == BUTTON_Pin)
    {
        BaseType_t xHigherPriorityTaskWoken = pdFALSE;

        /* 释放信号量（从 ISR） */
        xSemaphoreGiveFromISR(g_button_sem, &xHigherPriorityTaskWoken);

        /* 如果有高优先级任务被唤醒，进行上下文切换 */
        portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
    }
}

/* 按钮处理任务 */
void vButtonTask(void *pvParameters)
{
    while (1)
    {
        /* 等待信号量（阻塞） */
        if (xSemaphoreTake(g_button_sem, portMAX_DELAY) == pdTRUE)
        {
            printf("按钮按下！\r\n");

            /* 执行按钮处理逻辑 */
            HAL_GPIO_TogglePin(LED_GPIO_Port, LED_Pin);
        }
    }
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();

    /* 创建二值信号量 */
    g_button_sem = xSemaphoreCreateBinary();

    if (g_button_sem != NULL)
    {
        xTaskCreate(vButtonTask, "ButtonTask", 128, NULL, 2, NULL);
        vTaskStartScheduler();
    }

    while (1);
}
```

---

## 1.5 互斥锁（共享资源保护）

```c
#include "main.h"
#include "FreeRTOS.h"
#include "semphr.h"

/* 互斥锁 */
SemaphoreHandle_t g_uart_mutex;

/* 共享资源：UART */
UART_HandleTypeDef huart1;

/* 线程安全的打印函数 */
void thread_safe_print(char *str)
{
    /* 获取互斥锁 */
    if (xSemaphoreTake(g_uart_mutex, pdMS_TO_TICKS(100)) == pdTRUE)
    {
        /* 访问共享资源 */
        printf("%s", str);

        /* 释放互斥锁 */
        xSemaphoreGive(g_uart_mutex);
    }
}

/* 任务1：使用 UART */
void vTaskUart1(void *pvParameters)
{
    while (1)
    {
        thread_safe_print("Task1 正在使用 UART\r\n");
        vTaskDelay(pdMS_TO_TICKS(300));
    }
}

/* 任务2：使用 UART */
void vTaskUart2(void *pvParameters)
{
    while (1)
    {
        thread_safe_print("Task2 正在使用 UART\r\n");
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();

    /* 创建互斥锁（带优先级继承） */
    g_uart_mutex = xSemaphoreCreateMutex();

    if (g_uart_mutex != NULL)
    {
        xTaskCreate(vTaskUart1, "UartTask1", 128, NULL, 2, NULL);
        xTaskCreate(vTaskUart2, "UartTask2", 128, NULL, 2, NULL);

        vTaskStartScheduler();
    }

    while (1);
}
```

---

## 1.6 事件组

```c
#include "main.h"
#include "FreeRTOS.h"
#include "event_groups.h"

/* 事件位定义 */
#define EVENT_BIT_0      (1 << 0)  /* 0x01 */
#define EVENT_BIT_1      (1 << 1)  /* 0x02 */
#define EVENT_BIT_2      (1 << 2)  /* 0x04 */
#define EVENT_ALL_BITS   (EVENT_BIT_0 | EVENT_BIT_1 | EVENT_BIT_2)

/* 事件组 */
EventGroupHandle_t g_event_group;

/* 任务1：设置 EVENT_BIT_0 */
void vTask1(void *pvParameters)
{
    while (1)
    {
        vTaskDelay(pdMS_TO_TICKS(1000));
        xEventGroupSetBits(g_event_group, EVENT_BIT_0);
        printf("Task1 设置 EVENT_BIT_0\r\n");
    }
}

/* 任务2：设置 EVENT_BIT_1 */
void vTask2(void *pvParameters)
{
    while (1)
    {
        vTaskDelay(pdMS_TO_TICKS(1500));
        xEventGroupSetBits(g_event_group, EVENT_BIT_1);
        printf("Task2 设置 EVENT_BIT_1\r\n");
    }
}

/* 任务3：等待所有事件位 */
void vTask3(void *pvParameters)
{
    EventBits_t bits;

    while (1)
    {
        /* 等待所有位（AND 逻辑） */
        bits = xEventGroupWaitBits(g_event_group,
                                   EVENT_ALL_BITS,
                                   pdTRUE,   /* 退出时清除位 */
                                   pdTRUE,   /* 等待所有位（AND） */
                                   portMAX_DELAY);

        if ((bits & EVENT_ALL_BITS) == EVENT_ALL_BITS)
        {
            printf("Task3: 收到所有事件！bits=0x%02X\r\n", (unsigned int)bits);
        }
    }
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();

    /* 创建事件组 */
    g_event_group = xEventGroupCreate();

    if (g_event_group != NULL)
    {
        xTaskCreate(vTask1, "Task1", 128, NULL, 2, NULL);
        xTaskCreate(vTask2, "Task2", 128, NULL, 2, NULL);
        xTaskCreate(vTask3, "Task3", 128, NULL, 3, NULL);  /* 高优先级 */

        vTaskStartScheduler();
    }

    while (1);
}
```

---

## 1.7 任务通知

```c
#include "main.h"
#include "FreeRTOS.h"
#include "task.h"

/* 任务通知句柄 */
TaskHandle_t g_notify_task_handle;

/* 发送通知的任务 */
void vSenderTask(void *pvParameters)
{
    uint32_t count = 0;

    while (1)
    {
        vTaskDelay(pdMS_TO_TICKS(500));

        /* 发送通知（带累加值） */
        xTaskNotify(g_notify_task_handle, count, eSetValueWithOverwrite);

        printf("发送通知: %lu\r\n", count);
        count++;
    }
}

/* 接收通知的任务 */
void vReceiverTask(void *pvParameters)
{
    uint32_t notification_value;

    while (1)
    {
        /* 等待通知（阻塞） */
        if (xTaskNotifyWait(0, 0xFFFFFFFF, &notification_value,
                            portMAX_DELAY) == pdTRUE)
        {
            printf("收到通知: %lu\r\n", notification_value);
        }
    }
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();

    /* 创建接收任务并获取句柄 */
    xTaskCreate(vReceiverTask, "Receiver", 128, NULL, 2,
                &g_notify_task_handle);

    xTaskCreate(vSenderTask, "Sender", 128, NULL, 2, NULL);

    vTaskStartScheduler();

    while (1);
}
```
