# 中断最佳实践

本文档介绍 FromISR 函数使用规则、portYIELD_FROM_ISR 用法、NVIC 优先级配置等中断相关最佳实践。

---

## 2.1 FromISR 函数使用规则

### 基本规则

| 规则 | 说明 |
|------|------|
| **不阻塞** | FromISR 函数不能阻塞，只能在有限时间内返回 |
| **使用 pdFALSE** | `xTicksToWait` 应设为 0 或 `pdFALSE` |
| **检查返回值** | 检查返回值确定是否需要上下文切换 |
| **调用 portYIELD_FROM_ISR** | 如果 `*pxHigherPriorityTaskWoken` 为 pdTRUE，必须调用 |

### 正确用法

```c
void UART1_IRQHandler(void)
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;

    if (__HAL_UART_GET_FLAG(&huart1, UART_FLAG_RXNE) != RESET)
    {
        uint8_t data = (uint8_t)(huart1.Instance->DR & 0xFF);

        /* 从 ISR 发送数据到队列（不阻塞） */
        xQueueSendFromISR(g_uart_queue, &data, &xHigherPriorityTaskWoken);
    }

    /* 如果有高优先级任务被唤醒，进行上下文切换 */
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}
```

### 错误用法

```c
/* 错误：阻塞等待 */
void vBadIsrExample(void)
{
    uint8_t data;
    xQueueReceiveFromISR(g_uart_queue, &data, portMAX_DELAY);  /* 错误！ */
}

/* 错误：忘记调用 portYIELD_FROM_ISR */
void vBadIsrExample2(void)
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    xQueueSendFromISR(g_uart_queue, &data, &xHigherPriorityTaskWoken);
    /* 忘记调用 portYIELD_FROM_ISR(xHigherPriorityTaskWoken); */
}

/* 错误：传递错误的超时值 */
void vBadIsrExample3(void)
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    xQueueSendFromISR(g_uart_queue, &data, &xHigherPriorityTaskWoken);
    /* 传递了非 pdFALSE 值，虽然 FreeRTOS 会忽略，但仍不规范 */
}
```

### FromISR 函数列表

```c
/* 队列 FromISR */
BaseType_t xQueueSendFromISR(QueueHandle_t xQueue,
                             const void *pvItemToQueue,
                             BaseType_t *pxHigherPriorityTaskWoken);

BaseType_t xQueueReceiveFromISR(QueueHandle_t xQueue,
                                void *pvBuffer,
                                BaseType_t *pxHigherPriorityTaskWoken);

/* 信号量 FromISR */
BaseType_t xSemaphoreGiveFromISR(SemaphoreHandle_t xSemaphore,
                                 BaseType_t *pxHigherPriorityTaskWoken);

/* 事件组 FromISR */
BaseType_t xEventGroupSetBitsFromISR(EventGroupHandle_t xEventGroup,
                                     const EventBits_t uxBitsToSet,
                                     BaseType_t *pxHigherPriorityTaskWoken);

/* 任务通知 FromISR */
BaseType_t xTaskNotifyFromISR(TaskHandle_t xTaskToNotify,
                              uint32_t ulValue,
                              eNotifyAction eAction,
                              BaseType_t *pxHigherPriorityTaskWoken);

void vTaskNotifyGiveFromISR(TaskHandle_t xTaskHandle,
                            BaseType_t *pxHigherPriorityTaskWoken);
```

---

## 2.2 portYIELD_FROM_ISR 用法

### 语法

```c
void portYIELD_FROM_ISR(BaseType_t xHigherPriorityTaskWoken);
```

### 作用

当 `xHigherPriorityTaskWoken` 为 `pdTRUE` 时，触发 PendSV 中断进行上下文切换，唤醒等待该信号的高优先级任务。

### 完整示例

```c
void DMA1_Stream5_IRQHandler(void)
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    uint32_t flag = DMA1->HISR;

    /* 清除中断标志 */
    DMA1->HIFCR = flag;

    if (flag & DMA_HISR_TCIF5)
    {
        /* DMA 传输完成 */
        g_dma_complete = 1;

        /* 通知任务 */
        vTaskNotifyGiveFromISR(g_dma_task_handle,
                               &xHigherPriorityTaskWoken);
    }

    /* 必要时进行上下文切换 */
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}
```

### 简化版（FreeRTOS v10+）

```c
/* FreeRTOS v10.0+ 支持的简化宏 */
portYIELD_FROM_ISR(xHigherPriorityTaskWoken);

/* 等价于： */
if (xHigherPriorityTaskWoken == pdTRUE)
{
    portYIELD();
}
```

### 完整的中断处理流程

```c
void USART1_IRQHandler(void)
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;

    /* 处理中断源 */
    if (__HAL_UART_GET_FLAG(&huart1, UART_FLAG_RXNE) != RESET)
    {
        uint8_t data = huart1.Instance->DR;

        /* 发送数据到队列（FromISR，不阻塞） */
        if (xQueueSendFromISR(g_uart_queue, &data, &xHigherPriorityTaskWoken) == pdTRUE)
        {
            /* 队列接收成功，可能有高优先级任务被唤醒 */
        }
    }

    /* 处理其他中断源... */

    /* 清除中断标志 */
    __HAL_UART_CLEAR_PEFLAG(&huart1);

    /* 必要时进行上下文切换 */
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}
```

---

## 2.3 NVIC 优先级配置

### Cortex-M 优先级分组

```c
/* NVIC priority group 配置（STM32CubeMX 默认） */
NVIC_SetPriorityGrouping(NVIC_PRIORITYGROUP_4);  /* 4 位抢占优先级，0 位子优先级 */

/* 优先级数值越小，优先级越高 */

/* 优先级范围：0（最高）- 15（最低） */
```

### FreeRTOS 优先级要求

```c
/* FreeRTOSConfig.h */

/* 内核中断优先级（PendSV、SysTick） */
#define configKERNEL_INTERRUPT_PRIORITY 255  /* (15 << 4) */

/* 最大系统调用优先级（高于此值不能调用 FromISR API） */
#define configMAX_SYSCALL_INTERRUPT_PRIORITY 80  /* (5 << 4) */

/* 结论：
 * - 优先级 0-4：只能用于内核，不能调用任何 FreeRTOS API
 * - 优先级 5-15：可以调用 FromISR 结尾的 API
 * - 优先级 15：最低（PendSV、SysTick 默认）
 */
```

### 正确配置示例

```c
/* 定时器中断（需要触发任务）→ 优先级 5 */
HAL_NVIC_SetPriority(TIM6_DAC_IRQn, 5, 0);
HAL_NVIC_EnableIRQ(TIM6_DAC_IRQn);

/* UART 中断（需要 FromISR 发送队列）→ 优先级 6 */
HAL_NVIC_SetPriority(USART1_IRQn, 6, 0);
HAL_NVIC_EnableIRQ(USART1_IRQn);

/* DMA 中断（需要 FromISR 通知任务）→ 优先级 7 */
HAL_NVIC_SetPriority(DMA1_Stream5_IRQn, 7, 0);
HAL_NVIC_EnableIRQ(DMA1_Stream5_IRQn);

/* 外部中断（按钮唤醒）→ 优先级 10 */
HAL_NVIC_SetPriority(EXTI15_10_IRQn, 10, 0);
HAL_NVIC_EnableIRQ(EXTI15_10_IRQn);

/* 注意：数值越小优先级越高 */
```

### 错误配置示例

```c
/* 错误：外设中断优先级太低（高于 kernel） */
HAL_NVIC_SetPriority(USART1_IRQn, 4, 0);  /* 错误！会阻止中断服务程序调用 FreeRTOS API */

/* 正确：优先级 >= 5 */
HAL_NVIC_SetPriority(USART1_IRQn, 5, 0);  /* 正确 */
```

### 优先级数值与实际优先级的关系

```c
/* Cortex-M 的优先级配置寄存器是 8 位，但通常只使用高 4 位 */

/* 优先级数值左移 4 位后写入 NVIC */
NVIC_SetPriority(IRQn, priority << 4);

/* 示例 */
NVIC_SetPriority(USART1_IRQn, 6 << 4);  /* 优先级 6 */

/* 实际优先级计算 */
#define PRIORITY_SHIFT  4
#define NVIC_EncodePriority(Group, PreemptPriority, SubPriority) \
    (((PreemptPriority) & 0x07) << PRIORITY_SHIFT) | \
    ((SubPriority) & 0x00)
```

### 中断优先级配置最佳实践

```c
/* 1. 先设置优先级分组，再配置具体中断 */
void MX_NVIC_Init(void)
{
    /* 设置优先级分组：4 位抢占优先级，0 位子优先级 */
    HAL_NVIC_SetPriorityGrouping(NVIC_PRIORITYGROUP_4);

    /* 配置系统异常优先级（必须在分组之后） */
    HAL_NVIC_SetPriority(MemoryManagement_IRQn, 0, 0);
    HAL_NVIC_SetPriority(BusFault_IRQn, 0, 0);
    HAL_NVIC_SetPriority(UsageFault_IRQn, 0, 0);
    HAL_NVIC_SetPriority(SVCall_IRQn, 0, 0);
    HAL_NVIC_SetPriority(PendSV_IRQn, 15, 0);  /* 最低 */
    HAL_NVIC_SetPriority(SysTick_IRQn, 15, 0); /* 最低 */

    /* 配置外设中断 */
    HAL_NVIC_SetPriority(USART1_IRQn, 6, 0);
    HAL_NVIC_SetPriority(DMA1_Stream5_IRQn, 7, 0);
    HAL_NVIC_SetPriority(EXTI15_10_IRQn, 10, 0);

    /* 使能中断 */
    HAL_NVIC_EnableIRQ(USART1_IRQn);
    HAL_NVIC_EnableIRQ(DMA1_Stream5_IRQn);
    HAL_NVIC_EnableIRQ(EXTI15_10_IRQn);
}
```

---

## 中断设计最佳实践

### 1. 最小化 ISR 执行时间

```c
/* 不好：在 ISR 中做复杂处理 */
void vBadIsr(void)
{
    /* 复杂的数据处理 - 耗时 */
    process_data_in_isr();

    /* 发送队列 */
    xQueueSendFromISR(g_queue, &data, &xHigherPriorityTaskWoken);
}

/* 好：只在 ISR 中发送数据，复杂处理在任务中 */
void vGoodIsr(void)
{
    /* 快速获取数据 */
    uint8_t data = huart1.Instance->DR;

    /* 发送到队列，让任务处理 */
    xQueueSendFromISR(g_queue, &data, &xHigherPriorityTaskWoken);
}
```

### 2. 用任务通知替代信号量

```c
/* 用信号量 */
void vBadIsr(void)
{
    xSemaphoreGiveFromISR(g_sem, &xHigherPriorityTaskWoken);
}

void vTask(void)
{
    while (1)
    {
        xSemaphoreTake(g_sem, portMAX_DELAY);
        /* 处理 */
    }
}

/* 用任务通知（更轻量） */
void vGoodIsr(void)
{
    vTaskNotifyGiveFromISR(g_task_handle, &xHigherPriorityTaskWoken);
}

void vTask(void)
{
    while (1)
    {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        /* 处理 */
    }
}
```

### 3. 避免在 ISR 中做浮点运算

```c
/* 避免 */
void vBadIsr(void)
{
    float result = complex_calculation();  /* 耗时 */
    xQueueSendFromISR(g_queue, &result, &xHigherPriorityTaskWoken);
}

/* 推荐 */
void vGoodIsr(void)
{
    uint32_t raw_data = get_raw_data();
    xQueueSendFromISR(g_queue, &raw_data, &xHigherPriorityTaskWoken);
}

void vTask(void)
{
    while (1)
    {
        uint32_t data;
        xQueueReceive(g_queue, &data, portMAX_DELAY);

        /* 在任务中做浮点运算 */
        float result = (float)data * 0.123f;
    }
}
```

### 4. 避免在 ISR 中使用大内存

```c
/* 避免 */
void vBadIsr(void)
{
    uint8_t buffer[1024];  /* 栈上分配大数组 */
    /* 处理 */
}

/* 推荐 */
static uint8_t g_isr_buffer[1024];  /* 静态分配 */

void vGoodIsr(void)
{
    /* 使用静态缓冲区 */
    memcpy(g_isr_buffer, source, 1024);
    xQueueSendFromISR(g_queue, g_isr_buffer, &xHigherPriorityTaskWoken);
}
```
