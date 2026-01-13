# 调试工具配置

本文档介绍 SEGGER SystemView、Percep TRACEalyzer、ITM/SWO 等调试工具的配置方法。

---

## SEGGER SystemView（Keil/IAR 环境）

### 作用
- 实时系统分析
- 任务切换可视化
- 中断耗时统计
- CPU 使用率分析
- 事件追踪记录

### 配置步骤

#### 1. 添加 SystemView 库
- 下载 SEGGER SystemView 固件库
- 添加 `SEGGER_SYSVIEW.c` 到工程
- 添加 `SEGGER_SYSVIEW_FreeRTOS.c`（FreeRTOS 接口）

#### 2. 初始化 SystemView

```c
#include "SEGGER_SYSVIEW.h"

void vSystemView_Init(void)
{
    /* 初始化 J-Link（ST-Link 不支持 SystemView） */
    SEGGER_SYSVIEW_Init(SYSTEM_VIEW_TIMESTAMP_FREQ,
                        CPU_CORE_CLOCK,
                        &SYSVIEW_X_OS_Config,
                        &SEGGER_SYSVIEW_Conf);

    /* 开始录制 */
    SEGGER_SYSVIEW_Start();
}
```

#### 3. 配置 ITM/SWO

```c
/* ITM 端口使能 */
CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
ITM->TCR |= ITM_TCR_ITMENA_Msk;
ITM->TPR |= ITM_TPR_PRIVMASK_Msk;

/* SWO 引脚配置（根据芯片手册） */
GPIOB->MODER &= ~GPIO_MODER_MODE3_Msk;
GPIOB->MODER |= GPIO_MODER_MODE3_0;  /* AF */
GPIOB->AFR[0] &= ~GPIO_AFRH_AFRH3_Msk;
GPIOB->AFR[0] |= 0x0 << 12;          /* AF0 (SWO) */
```

#### 4. 任务追踪

```c
#include "SEGGER_SYSVIEW.h"

void vTaskExample(void *pvParameters)
{
    SEGGER_SYSVIEW_Print("任务启动");

    while (1)
    {
        SEGGER_SYSVIEW_RecordEnterTask();
        /* 任务代码 */
        SEGGER_SYSVIEW_RecordExitTask();

        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
```

---

## Percep TRACEalyzer（FreeRTOS 环境）

### 作用
- trace 事件录制和分析
- 时序图可视化
- 任务资源使用统计
- 性能瓶颈定位
- 内存使用追踪

### 配置步骤

#### 1. 启用 trace 功能

在 `FreeRTOSConfig.h` 中：

```c
#define configUSE_TRACE_FACILITY     1
#define configUSE_STATS_FORMATTING_FUNCTIONS 1
#define configRECORD_STACK_HIGH_ADDRESS 1
```

#### 2. 添加 trcRecorder.c

- 从 FreeRTOS+Trace 或 Percep TRACEalyzer 获取 `trcRecorder.c`
- 添加到工程
- 配置 `trcConfig.h`：

```c
#define TRC_CFG_TRACE_CONTROLLER_SUPPORTS_64_BIT_EVENTS 0
#define TRC_CFG_HARDWARE_PORT Cortex-M
#define TRC_CFG_FREERTOS_VERSION FREERTOS_VERSION
#define TRC_CFG_RECORDER_MODE TRC_RECORDER_MODE_STREAMING
```

#### 3. 初始化 recorder

```c
#include "trcRecorder.h"

void vTrace_Init(void)
{
    vTraceEnable(TRC_START);  /* 开始录制 */
}

void vTrace_Stop(void)
{
    vTraceDisable();  /* 停止录制 */
}
```

#### 4. 导出 trace 数据

```c
void vExportTrace(void)
{
    traceHandle trace_file;

    /* 打开文件 */
    trace_file = xTraceOpenWrite("w", "trace.ptd");
    if (trace_file != TRC_NULL)
    {
        /* 写入数据 */
        xTraceWrite(trace_file, NULL, 0);
        xTraceClose(trace_file);
    }
}
```

#### 5. 使用 TRACEalyzer 分析

1. 通过 J-Link/ST-Link 导出 `.ptd` 文件
2. 用 Percep TRACEalyzer 打开
3. 查看时序图、任务统计、资源使用

---

## ITM/SWO 配置步骤

### ST-Link 配置

```c
/* 使能 SWO 输出（ST-Link） */
volatile uint32_t *DBGMCU_CR = (volatile uint32_t *)0xE0042004;
*DBGMCU_CR |= 0x27;  /* TRACE_IOEN | TRACE_MODE_0 | TRACE_MODE_1 */

/* 配置 TPIU（Trace Port Interface Unit） */
TPI->ACPR = 0;  /* 1:1 分频 */
TPI->SPPR = 2;  /* SWO NRZ 编码 */
TPI->FFCR = 0;  /* 禁用 FIFO */

/* 使能 ITM 端口 0 */
ITM->TCR = 0x10009;  /* ITMENA | SyncFieldsEnable */
ITM->TER = 1;        /* 使能端口 0 */
```

### J-Link 配置

```c
/* J-Link SWO 初始化（Segger 提供） */
void SEGGER_SWO_Init(void)
{
    /* 配置 SWO 引脚 */
    GPIOA->MODER &= ~(GPIO_MODER_MODE9_Msk);
    GPIOA->MODER |= GPIO_MODER_MODE9_1;  /* AF */
    GPIOA->AFR[1] &= ~GPIO_AFRH_AFRH1_Msk;
    GPIOA->AFR[1] |= 0x0 << 4;  /* AF0 */

    /* 初始化 SWO 波特率 */
    SEGGER_SYSVIEW_SetSWOBaud(1000000);
}
```

---

## FreeRTOS 统计功能

### 任务状态统计

```c
#include "task.h"

void vTaskStatsPrint(void)
{
    TaskStatus_t *pxTaskStatusArray;
    UBaseType_t uxArraySize;
    uint32_t ulTotalRunTime;
    char buffer[512];

    /* 获取任务数 */
    uxArraySize = uxTaskGetNumberOfTasks();

    /* 分配内存 */
    pxTaskStatusArray = pvPortMalloc(uxArraySize * sizeof(TaskStatus_t));
    if (pxTaskStatusArray == NULL)
    {
        printf("内存分配失败\r\n");
        return;
    }

    /* 获取统计 */
    uxTaskGetSystemState(pxTaskStatusArray, uxArraySize,
                         &ulTotalRunTime);

    /* 打印统计 */
    snprintf(buffer, sizeof(buffer), "\r\n任务统计:\r\n");
    printf(buffer);

    for (UBaseType_t i = 0; i < uxArraySize; i++)
    {
        TaskStatus_t *pxTask = &pxTaskStatusArray[i];

        /* 计算 CPU 使用率 */
        uint32_t ulStatsAsPercentage =
            (pxTask->ulRunTimeCounter * 100UL) / ulTotalRunTime;

        snprintf(buffer, sizeof(buffer),
                 "%-16s 优先级: %2lu 状态: %c CPU: %2lu%% 堆栈: %lu\r\n",
                 pxTask->pcTaskName,
                 (unsigned long)pxTask->uxCurrentPriority,
                 (pxTask->eCurrentState == eRunning) ? 'R' :
                 (pxTask->eCurrentState == eReady) ? 'r' :
                 (pxTask->eCurrentState == eBlocked) ? 'B' :
                 (pxTask->eCurrentState == eSuspended) ? 'S' : '?',
                 (unsigned long)ulStatsAsPercentage,
                 (unsigned long)pxTask->usStackHighWaterMark);
        printf(buffer);
    }

    /* 释放内存 */
    vPortFree(pxTaskStatusArray);
}
```

### 运行时统计

```c
void vTaskRunTimeStats(void)
{
    TaskStatus_t *pxTaskStatusArray;
    UBaseType_t uxArraySize;
    uint32_t ulTotalRunTime;
    char buffer[256];

    uxArraySize = uxTaskGetNumberOfTasks();
    pxTaskStatusArray = pvPortMalloc(uxArraySize * sizeof(TaskStatus_t));

    if (pxTaskStatusArray != NULL)
    {
        uxTaskGetSystemState(pxTaskStatusArray, uxArraySize,
                             &ulTotalRunTime);

        printf("\r\n运行时统计:\r\n");
        printf("名称            运行时间(%)    周期数\r\n");
        printf("----------------------------------------\r\n");

        for (UBaseType_t i = 0; i < uxArraySize; i++)
        {
            TaskStatus_t *pxTask = &pxTaskStatusArray[i];
            uint32_t ulStatsAsPercentage =
                (pxTask->ulRunTimeCounter * 100UL) / ulTotalRunTime;

            snprintf(buffer, sizeof(buffer),
                     "%-16s %2lu.%02lu%%       %lu\r\n",
                     pxTask->pcTaskName,
                     (unsigned long)ulStatsAsPercentage,
                     (unsigned long)(ulStatsAsPercentage * 100) % 100,
                     (unsigned long)pxTask->ulRunTimeCounter);
            printf(buffer);
        }

        vPortFree(pxTaskStatusArray);
    }
}
```

### 堆栈溢出检测

```c
/* FreeRTOSConfig.h */
#define configCHECK_FOR_STACK_OVERFLOW 2

void vApplicationStackOverflowHook(TaskHandle_t xTask,
                                   char *pcTaskName)
{
    printf("堆栈溢出: %s\r\n", pcTaskName);
    while (1);  /* 进入死循环便于调试 */
}
```
