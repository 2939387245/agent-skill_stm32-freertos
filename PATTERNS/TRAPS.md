# 常见陷阱

本文档介绍 FreeRTOS 开发中常见的陷阱：优先级反转、堆栈溢出、死锁、资源泄漏。

---

## 3.1 优先级反转

### 问题说明

```
高优先级任务 ────────────┐
                         │ 等待资源
中优先级任务 ────┐       │
                 │ 持有资源
低优先级任务 ────┘       │

结果：高优先级任务被低优先级任务阻塞，中优先级任务也无法运行
```

### 优先级反转的危害

1. 高优先级任务等待低优先级任务释放资源
2. 中优先级任务抢占 CPU，导致低优先级任务无法运行
3. 高优先级任务被无限期阻塞

### 解决方案：优先级继承

```c
/* 互斥锁自动实现优先级继承 */
SemaphoreHandle_t xMutex = xSemaphoreCreateMutex();

/* 使用互斥锁保护共享资源 */
void vAccessResource(void)
{
    if (xSemaphoreTake(xMutex, pdMS_TO_TICKS(100)) == pdPASS)
    {
        /* 访问共享资源 */
        // ...

        xSemaphoreGive(xMutex);
    }
}
```

### 完整示例

```c
#include "main.h"
#include "FreeRTOS.h"
#include "semphr.h"

/* 任务优先级定义 */
#define PRIORITY_HIGH    3
#define PRIORITY_MEDIUM  2
#define PRIORITY_LOW     1

SemaphoreHandle_t g_resource_mutex;
uint32_t g_shared_resource = 0;

/* 低优先级任务：占用资源时间长 */
void vLowPriorityTask(void *pvParameters)
{
    while (1)
    {
        if (xSemaphoreTake(g_resource_mutex, portMAX_DELAY) == pdPASS)
        {
            g_shared_resource++;
            printf("低优先级任务：资源值 = %lu\r\n", g_shared_resource);

            /* 模拟长时间占用 */
            vTaskDelay(pdMS_TO_TICKS(2000));

            xSemaphoreGive(g_resource_mutex);
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

/* 高优先级任务：快速访问资源 */
void vHighPriorityTask(void *pvParameters)
{
    TickType_t start_time;

    while (1)
    {
        start_time = xTaskGetTickCount();

        if (xSemaphoreTake(g_resource_mutex, pdMS_TO_TICKS(500)) == pdPASS)
        {
            g_shared_resource++;
            printf("高优先级任务：资源值 = %lu\r\n", g_shared_resource);
            xSemaphoreGive(g_resource_mutex);
        }
        else
        {
            printf("高优先级任务：等待超时\r\n");
        }

        printf("高优先级任务：等待时间 = %lu ms\r\n",
               pdTICKS_TO_MS(xTaskGetTickCount() - start_time));

        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

/* 解决优先级反转问题 */
void vPriorityInversionDemo(void)
{
    /* 使用互斥锁，自动启用优先级继承 */
    g_resource_mutex = xSemaphoreCreateMutex();

    /* 创建任务 */
    xTaskCreate(vLowPriorityTask, "Low", 128, NULL,
                PRIORITY_LOW, NULL);
    xTaskCreate(vHighPriorityTask, "High", 128, NULL,
                PRIORITY_HIGH, NULL);
}
```

### 优先级继承原理

```c
/* xSemaphoreCreateMutex 内部实现 */
SemaphoreHandle_t xSemaphoreCreateMutex(void)
{
    SemaphoreHandle_t xSemaphore;

    /* 创建二值信号量 */
    xSemaphore = xSemaphoreCreateBinary();

    if (xSemaphore != NULL)
    {
        /* 设置为互斥锁模式，启用优先级继承 */
        xSemaphore->ucType = queueQUEUE_TYPE_MUTEX;

        /* 当高优先级任务等待互斥锁时，提升持有者任务的优先级 */
        prvLockMutex(xSemaphore);
    }

    return xSemaphore;
}
```

---

## 3.2 堆栈溢出

### 检测方法

```c
/* FreeRTOSConfig.h */
#define configCHECK_FOR_STACK_OVERFLOW 2  /* 方法 2：检查堆栈指针 */

void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
    printf("堆栈溢出！任务: %s\r\n", pcTaskName);

    /* 进入死循环，便于调试 */
    while (1)
    {
        HAL_GPIO_TogglePin(LED_GPIO_Port, LED_Pin);
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
```

### 检测方法对比

| 方法 | 说明 | 配置 |
|------|------|------|
| 方法 1 | 检查堆栈指针是否超出范围 | `configCHECK_FOR_STACK_OVERFLOW = 1` |
| 方法 2 | 检查堆栈指针和堆栈内容 | `configCHECK_FOR_STACK_OVERFLOW = 2` |
| 方法 3 | 任务上下文切换时检查 | `configCHECK_FOR_STACK_OVERFLOW = 3` |

### 预防措施

```c
/* 1. 合理设置堆栈大小 */
#define TASK_STACK_SIZE 256  /* 256 字 = 1024 字节 */

/* 2. 避免大数组在栈上分配 */
#define LARGE_BUFFER_SIZE 1024

/* 错误：栈上分配大数组 */
void vBadTask(void *pvParameters)
{
    uint8_t large_buffer[1024];  /* 可能溢出 */
    // ...
}

/* 正确：静态分配 */
static uint8_t g_buffer[LARGE_BUFFER_SIZE];  /* 静态 */

void vGoodTask(void *pvParameters)
{
    /* 使用静态缓冲区 */
    memcpy(g_buffer, source, LARGE_BUFFER_SIZE);
}

/* 3. 定期检查堆栈使用 */
void vStackMonitorTask(void *pvParameters)
{
    TaskHandle_t tasks[10];
    UBaseType_t count;

    while (1)
    {
        count = uxTaskGetSystemState(tasks, 10, NULL);

        for (UBaseType_t i = 0; i < count; i++)
        {
            UBaseType_t watermark = uxTaskGetStackHighWaterMark(tasks[i]);
            TaskStatus_t *status = pxTaskGetTaskStatus(tasks[i]);

            printf("任务 %s: 堆栈剩余 %lu 字\r\n",
                   status->pcTaskName, watermark);

            /* 警告 */
            if (watermark < 20)
            {
                printf("警告: %s 堆栈即将耗尽！\r\n", status->pcTaskName);
            }
        }

        vTaskDelay(pdMS_TO_TICKS(5000));
    }
}
```

### 堆栈大小估算规则

```c
/* 任务堆栈估算（字为单位） */
#define TASK_STACK_DEPTH_BASE    128   /* 基础需求 */
#define TASK_STACK_DEPTH_UART    256   /* UART 处理任务 */
#define TASK_STACK_DEPTH_COM     512   /* 通信任务 */
#define TASK_STACK_DEPTH_LARGE   1024  /* 复杂任务 */

/* 规则：
 * - 简单循环任务: 128-256 字
 * - 有字符串处理: +64-128 字
 * - 有递归调用: +256 字
 * - 有局部大数组: +数组大小
 * - 使用 printf: +50-100 字
 */

/* 示例：复杂任务 */
xTaskCreate(vComplexTask, "Complex", 512,  /* 512 字堆栈 */
            NULL, osPriorityNormal, NULL);
```

---

## 3.3 死锁

### 问题说明

两个或多个任务相互等待对方释放资源，导致永久阻塞。

### 死锁的四个必要条件

1. **互斥**：资源不能被共享，只能独占
2. **持有并等待**：任务持有资源，同时等待其他资源
3. **非抢占**：资源不能被强制夺走
4. **循环等待**：任务间形成等待环

### 示例

```c
/* 死锁示例 */
void vDeadlockExample(void)
{
    SemaphoreHandle_t mutex_a = xSemaphoreCreateMutex();
    SemaphoreHandle_t mutex_b = xSemaphoreCreateMutex();

    /* 任务1：先获取 A，再获取 B */
    void vTask1(void *pvParameters)
    {
        while (1)
        {
            xSemaphoreTake(mutex_a, portMAX_DELAY);
            vTaskDelay(1);  /* 让出 CPU */
            xSemaphoreTake(mutex_b, portMAX_DELAY);  /* 等待 B */

            // 使用资源

            xSemaphoreGive(mutex_b);
            xSemaphoreGive(mutex_a);
        }
    }

    /* 任务2：先获取 B，再获取 A */
    void vTask2(void *pvParameters)
    {
        while (1)
        {
            xSemaphoreTake(mutex_b, portMAX_DELAY);
            vTaskDelay(1);  /* 让出 CPU */
            xSemaphoreTake(mutex_a, portMAX_DELAY);  /* 等待 A */

            // 使用资源

            xSemaphoreGive(mutex_a);
            xSemaphoreGive(mutex_b);
        }
    }

    /* 可能发生死锁：
     * 1. 任务1获取A，任务2获取B
     * 2. 任务1尝试获取B（被任务2持有）
     * 3. 任务2尝试获取A（被任务1持有）
     * 4. 双方永久等待
     */
}
```

### 解决方案

```c
/* 解决方案1：统一获取顺序 */
void vTask1Fixed(void *pvParameters)
{
    while (1)
    {
        /* 始终先获取 A，再获取 B */
        xSemaphoreTake(mutex_a, portMAX_DELAY);
        xSemaphoreTake(mutex_b, portMAX_DELAY);

        // 使用资源

        xSemaphoreGive(mutex_b);
        xSemaphoreGive(mutex_a);
    }
}

void vTask2Fixed(void *pvParameters)
{
    while (1)
    {
        /* 同样先获取 A，再获取 B */
        xSemaphoreTake(mutex_a, portMAX_DELAY);
        xSemaphoreTake(mutex_b, portMAX_DELAY);

        // 使用资源

        xSemaphoreGive(mutex_b);
        xSemaphoreGive(mutex_a);
    }
}

/* 解决方案2：使用单一互斥锁 */
void vTaskWithSingleMutex(void *pvParameters)
{
    SemaphoreHandle_t resource_mutex = xSemaphoreCreateMutex();

    while (1)
    {
        /* 只使用一个互斥锁 */
        if (xSemaphoreTake(resource_mutex, portMAX_DELAY) == pdPASS)
        {
            /* 访问所有共享资源 */
            // access_resource_a();
            // access_resource_b();

            xSemaphoreGive(resource_mutex);
        }
    }
}

/* 解决方案3：超时获取 */
void vTaskWithTimeout(void *pvParameters)
{
    while (1)
    {
        if (xSemaphoreTake(mutex_a, pdMS_TO_TICKS(100)) == pdPASS)
        {
            if (xSemaphoreTake(mutex_b, pdMS_TO_TICKS(100)) == pdPASS)
            {
                // 使用资源
                xSemaphoreGive(mutex_b);
            }
            else
            {
                /* 超时，释放已获取的锁 */
                printf("获取 mutex_b 超时，释放 mutex_a\r\n");
                xSemaphoreGive(mutex_a);
            }
        }
        else
        {
            vTaskDelay(pdMS_TO_TICKS(50));
        }
    }
}
```

---

## 3.4 资源泄漏

### 问题说明

资源（内存、信号量、队列）未正确释放，导致系统资源耗尽。

### 内存泄漏

```c
/* 内存泄漏示例 */
void vMemoryLeakTask(void *pvParameters)
{
    while (1)
    {
        /* 每次循环分配内存但不释放 */
        char *buffer = pvPortMalloc(256);
        if (buffer != NULL)
        {
            process_data(buffer);
            /* 忘记 vPortFree(buffer); */
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

/* 正确做法：在任务外部分配 */
char *g_buffer = NULL;

void vNoLeakTask(void *pvParameters)
{
    g_buffer = pvPortMalloc(256);

    if (g_buffer != NULL)
    {
        while (1)
        {
            process_data(g_buffer);
            vTaskDelay(pdMS_TO_TICKS(100));
        }

        vPortFree(g_buffer);  /* 任务删除时释放 */
    }
}
```

### 队列泄漏

```c
/* 队列泄漏示例 */
void vQueueLeakTask(void *pvParameters)
{
    QueueHandle_t local_queue;

    while (1)
    {
        /* 每次循环创建新队列 */
        local_queue = xQueueCreate(10, sizeof(uint32_t));

        /* 发送数据 */
        uint32_t data = HAL_GetTick();
        xQueueSend(local_queue, &data, 0);

        vTaskDelay(pdMS_TO_TICKS(1000));

        /* 忘记删除队列 */
        /* vQueueDelete(local_queue); */
    }
}

/* 正确做法：使用全局队列 */
QueueHandle_t g_global_queue;

void vCorrectQueueTask(void *pvParameters)
{
    /* 初始化时创建队列 */
    g_global_queue = xQueueCreate(10, sizeof(uint32_t));

    while (1)
    {
        uint32_t data = HAL_GetTick();
        xQueueSend(g_global_queue, &data, 0);

        vTaskDelay(pdMS_TO_TICKS(1000));
    }

    /* 不需要删除，因为队列是全局的 */
}

/* 或在任务结束时清理 */
void vTaskWithCleanup(void *pvParameters)
{
    QueueHandle_t local_queue = xQueueCreate(10, sizeof(uint32_t));

    if (local_queue != NULL)
    {
        while (1)
        {
            /* 使用队列 */
            if (should_exit())
            {
                break;
            }
        }

        /* 任务结束前清理 */
        vQueueDelete(local_queue);
    }

    vTaskDelete(NULL);  /* 删除自己 */
}
```

### 信号量泄漏

```c
/* 信号量泄漏示例 */
void vSemaphoreLeakTask(void *pvParameters)
{
    while (1)
    {
        SemaphoreHandle_t sem = xSemaphoreCreateBinary();

        /* 使用信号量 */
        xSemaphoreTake(sem, portMAX_DELAY);

        vTaskDelay(pdMS_TO_TICKS(1000));

        /* 忘记删除 */
        /* vSemaphoreDelete(sem); */
    }
}

/* 正确做法：使用全局信号量 */
SemaphoreHandle_t g_button_sem;

void vButtonTaskCorrect(void *pvParameters)
{
    /* 初始化时创建 */
    g_button_sem = xSemaphoreCreateBinary();

    while (1)
    {
        if (xSemaphoreTake(g_button_sem, portMAX_DELAY) == pdTRUE)
        {
            /* 处理按钮事件 */
        }
    }
}

/* 清理函数 */
void vCleanup(void)
{
    if (g_button_sem != NULL)
    {
        vSemaphoreDelete(g_button_sem);
        g_button_sem = NULL;
    }
}
```

### 资源管理最佳实践

```c
/* 1. 资源在初始化时创建 */
typedef struct {
    QueueHandle_t queue;
    SemaphoreHandle_t mutex;
    TaskHandle_t task;
} AppResources_t;

AppResources_t g_app_resources;

void vAppInit(void)
{
    /* 创建所有资源 */
    g_app_resources.queue = xQueueCreate(10, sizeof(uint32_t));
    g_app_resources.mutex = xSemaphoreCreateMutex();
    xTaskCreate(vTask, "App", 256, NULL, 2, &g_app_resources.task);
}

/* 2. 资源在清理时释放 */
void vAppCleanup(void)
{
    if (g_app_resources.task != NULL)
    {
        vTaskDelete(g_app_resources.task);
        g_app_resources.task = NULL;
    }

    if (g_app_resources.mutex != NULL)
    {
        vSemaphoreDelete(g_app_resources.mutex);
        g_app_resources.mutex = NULL;
    }

    if (g_app_resources.queue != NULL)
    {
        vQueueDelete(g_app_resources.queue);
        g_app_resources.queue = NULL;
    }
}
```
