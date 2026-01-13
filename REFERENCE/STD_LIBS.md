# 标准库集成

本文档介绍 stdio.h、string.h、stdlib.h 与 FreeRTOS 的集成使用方法。

---

## stdio.h（printf 重定向）

### ITM_SendChar（SWO 输出）

```c
#include <stdio.h>

/* 重定向 printf 到 ITM/SWO */
int __attribute__((weak)) _write(int file, char *ptr, int len)
{
    (void)file;
    int i;
    for (i = 0; i < len; i++)
    {
        ITM_SendChar(ptr[i]);  /* 通过 SWO 输出 */
    }
    return len;
}

/* 使用示例 */
void vTaskITM(void *pvParameters)
{
    while (1)
    {
        printf("堆栈剩余: %lu 字节\r\n",
               uxTaskGetStackHighWaterMark(NULL));
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

### UART 重定向

```c
#include <stdio.h>
#include "usart.h"

int __attribute__((weak)) _write(int file, char *ptr, int len)
{
    (void)file;
    HAL_UART_Transmit(&huart1, (uint8_t *)ptr, len, HAL_MAX_DELAY);
    return len;
}
```

### snprintf 安全格式化

```c
#include <stdio.h>
#include <string.h>

void vTaskPrintStatus(void *pvParameters)
{
    char buffer[128];
    TaskStatus_t *pxTaskStatusArray;
    uint32_t ulTotalRunTime, ulStatsAsPercentage;

    /* 获取任务状态 */
    UBaseType_t uxArraySize = uxTaskGetNumberOfTasks();
    pxTaskStatusArray = pvPortMalloc(uxArraySize * sizeof(TaskStatus_t));

    if (pxTaskStatusArray != NULL)
    {
        uxTaskGetSystemState(pxTaskStatusArray, uxArraySize,
                             &ulTotalRunTime);

        /* 安全格式化（防止缓冲区溢出） */
        snprintf(buffer, sizeof(buffer),
                 "任务数: %lu\r\n", uxArraySize);
        HAL_UART_Transmit(&huart1, (uint8_t *)buffer,
                          strlen(buffer), HAL_MAX_DELAY);

        vPortFree(pxTaskStatusArray);
    }
}
```

---

## string.h（DMA 内存操作）

### memcpy 在 DMA 中的使用

```c
#include <string.h>
#include "dma.h"

#define RX_BUFFER_SIZE 256

uint8_t g_rx_buffer[RX_BUFFER_SIZE];
uint8_t g_rx_temp[RX_BUFFER_SIZE];

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1)
    {
        /* 将接收数据复制到处理缓冲区 */
        memcpy(g_rx_temp, g_rx_buffer, RX_BUFFER_SIZE);

        /* 通知处理任务 */
        BaseType_t xHigherPriorityTaskWoken = pdFALSE;
        xQueueSendFromISR(g_uart_queue, g_rx_temp,
                          &xHigherPriorityTaskWoken);
        portYIELD_FROM_ISR(xHigherPriorityTaskWoken);

        /* 重新启动 DMA 接收 */
        HAL_UART_Receive_IT(&huart1, g_rx_buffer, RX_BUFFER_SIZE);
    }
}
```

### memset 初始化控制块

```c
#include <string.h>

StaticTask_t xTaskBuffer;
StackType_t xStack[128];

void vTaskCreateStaticExample(void)
{
    /* 清零控制块（推荐） */
    memset(&xTaskBuffer, 0, sizeof(StaticTask_t));

    /* 创建静态任务 */
    xTaskCreateStatic(vTaskFunction, "StaticTask",
                      128, NULL, osPriorityNormal,
                      xStack, &xTaskBuffer);
}
```

---

## stdlib.h（动态内存注意事项）

### 避免在任务中频繁 malloc/free

```c
#include <stdlib.h>
#include "main.h"

/* 不推荐：每次处理都分配内存 */
void vTaskBadExample(void *pvParameters)
{
    while (1)
    {
        char *p_data = pvPortMalloc(256);  /* 频繁分配 */
        if (p_data != NULL)
        {
            /* 处理数据 */
            process_data(p_data);
            vPortFree(p_data);  /* 释放 */
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

/* 推荐：使用静态缓冲区池 */
#define BUFFER_POOL_SIZE 10
#define BUFFER_SIZE 256

static uint8_t g_buffer_pool[BUFFER_POOL_SIZE][BUFFER_SIZE];
static uint8_t g_buffer_used[BUFFER_POOL_SIZE];

void *pvAllocateBuffer(void)
{
    for (int i = 0; i < BUFFER_POOL_SIZE; i++)
    {
        if (g_buffer_used[i] == 0)
        {
            g_buffer_used[i] = 1;
            memset(g_buffer_pool[i], 0, BUFFER_SIZE);
            return g_buffer_pool[i];
        }
    }
    return NULL;  /* 池已满 */
}

void vFreeBuffer(void *p_buffer)
{
    for (int i = 0; i < BUFFER_POOL_SIZE; i++)
    {
        if (g_buffer_pool[i] == p_buffer)
        {
            g_buffer_used[i] = 0;
            break;
        }
    }
}
```

### pvPortMalloc vs malloc

```c
/* 使用 FreeRTOS 内存分配函数 */
void *pvPortMalloc(size_t xSize);    /* 分配内存 */
void vPortFree(void *pv);             /* 释放内存 */

/* 与标准库的区别：
 * - pvPortMalloc 使用 FreeRTOS 的 heap 内存管理
 * - 可以与 xTaskCreate 等函数配合使用
 * - 支持静态分配策略
 */
```

### heap 内存监控

```c
void vHeapStatsPrint(void)
{
    HeapStats_t heap_stats;

    xPortGetHeapStats(&heap_stats);

    printf("\r\nHeap 统计:\r\n");
    printf("  可分配最小: %lu 字节\r\n", heap_stats.xMinimumEverFreeBytesRemaining);
    printf("  当前可用: %lu 字节\r\n", heap_stats.xAvailableHeapSpaceInBytes);
    printf("  分配块数: %lu\r\n", heap_stats.xNumberOfAllocations);
    printf("  释放块数: %lu\r\n", heap_stats.xNumberOfFrees);
    printf("  最大分配: %lu 字节\r\n", heap_stats.xSizeOfLargestFreeBlockInBytes);
}
```
