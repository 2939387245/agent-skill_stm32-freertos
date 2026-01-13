# STM32 + FreeRTOS Skill 用户指南

> **重要提示**：本文档仅供**你（用户）阅读**，AI 不会读取本文档。本文档帮助你理解每个文件的用途，以及如何让 AI 读取正确的文件来回答你的问题。

---

## 这个 Skill 是什么？

这是一个专门帮助你在 **STM32 微控制器** 上使用 **FreeRTOS 实时操作系统** 的工具。AI 可以：

- **帮你写代码**：创建任务、队列、信号量、外设驱动
- **帮你审查代码**：分析问题、优化性能、排查错误
- **教你理解概念**：解释调度机制、通信方式、调试方法

---

## 文件结构总览

这个 Skill 由以下文件组成：

```
stm32-freertos/
├── SKILL.md              ← AI 唯一会自动读取的主文件
├── USER_GUIDE.md         ← 你正在看的文件（AI 不读取）
├── REFERENCE/            ← API 参考手册（4 个文件）
│   ├── FREERTOS_API.md
│   ├── STD_LIBS.md
│   ├── HAL_DRIVERS.md
│   └── DEBUG_TOOLS.md
├── EXAMPLES/             ← 代码示例（3 个文件）
│   ├── BASIC.md
│   ├── DRIVERS.md
│   └── ADVANCED.md
├── PATTERNS/             ← 设计模式与陷阱（3 个文件）
│   ├── DESIGN.md
│   ├── INTERRUPT.md
│   └── TRAPS.md
└── scripts/
    └── freertos_config_check.py
```

---

## REFERENCE/ 目录：API 参考手册

这个目录告诉你 FreeRTOS 的 API 怎么用，HAL 库怎么和 FreeRTOS 配合。

---

### REFERENCE/FREERTOS_API.md

**什么时候读这个？**

当你想知道某个函数怎么用时：

- "`xTaskCreate` 需要什么参数？"
- "`xQueueSend` 和 `xQueueSendFromISR` 有什么区别？"
- "CMSIS-RTOS v2 和原生 FreeRTOS API 有什么不同？"
- "任务通知怎么用？"

**包含内容：**

```
1. 原生 FreeRTOS API（v10+）
   ├── 任务管理
   │   ├── xTaskCreate - 动态创建任务
   │   ├── xTaskCreateStatic - 静态创建任务
   │   ├── vTaskDelete - 删除任务
   │   ├── vTaskDelay - 相对延时
   │   ├── vTaskDelayUntil - 绝对延时
   │   ├── vTaskPrioritySet - 设置优先级
   │   └── uxTaskPriorityGet - 获取优先级
   │
   ├── 队列
   │   ├── xQueueCreate - 创建队列
   │   ├── xQueueSend - 发送数据
   │   ├── xQueueReceive - 接收数据
   │   └── xQueueSendFromISR - 中断中发送
   │
   ├── 信号量
   │   ├── xSemaphoreCreateBinary - 二值信号量
   │   ├── xSemaphoreCreateCounting - 计数信号量
   │   ├── xSemaphoreCreateMutex - 互斥锁
   │   ├── xSemaphoreTake - 获取信号量
   │   └── xSemaphoreGive - 释放信号量
   │
   ├── 事件组
   │   ├── xEventGroupCreate - 创建事件组
   │   ├── xEventGroupSetBits - 设置事件位
   │   ├── xEventGroupWaitBits - 等待事件位
   │   └── xEventGroupSetBitsFromISR - 中断中设置
   │
   └── 任务通知
       ├── xTaskNotify - 发送通知
       ├── xTaskNotifyFromISR - 中断中发送
       └── xTaskNotifyWait - 等待通知

2. CMSIS-RTOS v2 API
   ├── osThreadNew - 创建线程
   ├── osDelay - 延时
   ├── osMessageQueueNew - 创建消息队列
   ├── osSemaphoreNew - 创建信号量
   ├── osMutexNew - 创建互斥锁
   └── osEventFlagsNew - 创建事件标志
```

**典型问题：** "`xQueueSend` 的超时参数怎么用？"

---

### REFERENCE/STD_LIBS.md

**什么时候读这个？**

当你想使用标准库与 FreeRTOS 配合时：

- "怎么让 `printf` 输出到串口？"
- "DMA 传输中能用 `memcpy` 吗？"
- "为什么不应该在任务里频繁 `malloc/free`？"
- "怎么把 printf 重定向到 ITM/SWO？"

**包含内容：**

```
1. stdio.h - printf 重定向
   ├── 重定向到 ITM/SWO（通过调试器输出）
   │   ├── ITM_SendChar 实现
   │   ├── __attribute__((weak)) _write 重写
   │   └── 验证方法
   │
   └── 重定向到 UART（通过串口输出）
       ├── HAL_UART_Transmit 重写
       ├── 波特率配置
       └── 阻塞 vs 非阻塞

2. string.h - 内存操作
   ├── memcpy 配合 DMA
   │   ├── DMA 接收完成回调中使用
   │   ├── 缓冲区复制
   │   └── 注意事项
   │
   └── memset 初始化
       ├── 控制块清零
       ├── 缓冲区初始化
       └── 静态 vs 动态

3. stdlib.h - 内存管理
   ├── pvPortMalloc / vPortFree（FreeRTOS 内存分配）
   │   ├── 与标准 malloc/free 的区别
   │   ├── 内存池
   │   └── 避免碎片
   │
   └── 动态内存注意事项
       ├── 频繁分配释放的问题
       ├── 内存泄漏检测
       └── 静态分配优先
```

**典型问题：** "怎么在 STM32 上使用 printf？"

---

### REFERENCE/HAL_DRIVERS.md

**什么时候读这个？**

当你需要写外设与 FreeRTOS 配合的代码时：

- "UART 接收不定长数据怎么做？"
- "ADC 连续采集怎么通知任务？"
- "I2C 传感器怎么和 FreeRTOS 结合？"
- "定时器怎么触发任务？"

**包含内容：**

```
1. UART DMA + 队列（不定长数据接收）
   ├── IDLE 中断检测接收完成
   ├── DMA 配置
   ├── 队列传递数据
   ├── 头文件结构
   └── 完整驱动代码

2. ADC DMA + 任务通知
   ├── 连续转换模式
   ├── DMA 配置
   ├── HAL_ADC_ConvCpltCallback
   ├── 任务通知机制
   └── 代码实现

3. I2C 传感器读取
   ├── 主模式：读取传感器数据
   │   ├── MPU6050 示例
   │   ├── BME280 示例
   │   └── 超时处理
   │
   └── 从模式：响应主设备请求
       ├── I2C 从地址配置
       └── 回调处理

4. TIM 定时器 + 任务触发
   ├── 定时器中断配置
   ├── 任务通知机制
   ├── 周期任务实现
   └── PWM 输出
```

**典型问题：** "怎么用 DMA 实现 UART 不定长数据接收？"

---

### REFERENCE/DEBUG_TOOLS.md

**什么时候读这个？**

当你需要调试和分析系统时：

- "怎么用 SystemView 看任务切换？"
- "TRACEalyzer 怎么配置？"
- "怎么打印任务运行时间？"
- "ITM/SWO 怎么配置？"

**包含内容：**

```
1. SEGGER SystemView（Keil/IAR 环境）
   ├── 作用
   │   ├── 实时系统分析
   │   ├── 任务切换可视化
   │   ├── 中断耗时统计
   │   └── CPU 使用率分析
   │
   ├── 配置步骤
   │   ├── 添加 SystemView 库
   │   ├── 初始化 SEGGER_SYSVIEW_Init()
   │   └── 配置 ITM/SWO
   │
   └── 使用方法
       ├── 开始录制
       ├── 分析任务切换
       └── 查找性能瓶颈

2. Percep TRACEalyzer（FreeRTOS 环境）
   ├── 作用
   │   ├── trace 事件录制
   │   ├── 时序图可视化
   │   ├── 任务资源统计
   │   └── 性能瓶颈定位
   │
   ├── 配置步骤
   │   ├── 启用 trace 功能
   │   ├── 添加 trcRecorder.c
   │   └── 配置 trcConfig.h
   │
   └── 使用方法
       ├── 导出 .ptd 文件
       ├── 用 TRACEalyzer 打开
       └── 分析结果

3. ITM/SWO 配置
   ├── ST-Link 配置
   │   ├── 使能 SWO 输出
   │   ├── 配置 TPIU
   │   └── 验证方法
   │
   └── J-Link 配置
       ├── SWO 初始化
       └── 波特率配置

4. FreeRTOS 统计功能
   ├── 任务状态统计
   │   ├── vTaskList 用法
   │   ├── uxTaskGetStackHighWaterMark
   │   └── 打印任务信息
   │
   └── 运行时统计
       ├── xTaskGetSystemState
       ├── CPU 使用率计算
       └── 堆栈溢出检测
```

**典型问题：** "怎么用 SystemView 分析任务切换？"

---

## EXAMPLES/ 目录：代码示例

这个目录给你完整的、可直接使用的代码。

---

### EXAMPLES/BASIC.md

**什么时候读这个？**

当你需要基础组件的示例时：

- "怎么创建第一个任务？"
- "队列怎么用？"
- "信号量怎么同步任务？"
- "互斥锁怎么保护共享资源？"
- "事件组怎么做多条件触发？"
- "任务通知怎么用？"

**包含内容：**

```
1. 动态任务创建
   ├── 任务函数定义
   ├── xTaskCreate 参数说明
   ├── 任务优先级设置
   └── 完整可运行示例

2. 静态任务创建
   ├── 静态控制块和堆栈
   ├── xTaskCreateStatic 用法
   └── 优点和适用场景

3. 队列 - 生产者消费者
   ├── 队列创建
   ├── 生产者任务：产生数据
   ├── 消费者任务：处理数据
   ├── 超时处理
   └── 完整示例代码

4. 二值信号量 - 任务同步
   ├── 信号量创建
   ├── 中断中释放信号量
   │   ├── HAL_GPIO_EXTI_Callback
   │   └── xSemaphoreGiveFromISR
   │
   └── 任务中获取信号量
       ├── xSemaphoreTake
       └── 按钮消抖示例

5. 互斥锁 - 共享资源保护
   ├── xSemaphoreCreateMutex
   ├── 优先级继承
   ├── UART 互斥访问
   └── 完整示例

6. 事件组 - 多条件触发
   ├── xEventGroupCreate
   ├── xEventGroupSetBits
   ├── xEventGroupWaitBits
   ├── AND/OR 逻辑
   └── 完整示例

7. 任务通知 - 轻量级通信
   ├── xTaskNotify 发送
   ├── xTaskNotifyWait 接收
   ├── 中断中通知
   └── 与队列/信号量的对比
```

**典型问题：** "给我一个完整的队列生产者-消费者示例"

---

### EXAMPLES/DRIVERS.md

**什么时候读这个？**

当你需要外设驱动模板时：

- "给我一个 UART DMA 驱动"
- "ADC DMA 采集怎么做？"
- "I2C 传感器驱动怎么写？"
- "printf 重定向怎么实现？"

**包含内容：**

```
1. UART DMA + 队列 + IDLE 中断（完整驱动）
   ├── 头文件结构（uart_driver.h）
   │   ├── 队列定义
   │   ├── 函数声明
   │   └── 宏定义
   │
   ├── 实现文件（uart_driver.c）
   │   ├── MX_UART1_Init 初始化
   │   ├── HAL_UART_IDLECallback
   │   ├── HAL_UART_RxCpltCallback
   │   ├── vUartRxTask 接收任务
   │   └── 数据处理任务
   │
   └── 使用方法
       ├── 初始化调用
       ├── 任务创建
       └── 数据获取

2. ADC DMA + 任务通知（完整驱动）
   ├── 头文件结构（adc_driver.h）
   ├── 实现文件（adc_driver.c）
   │   ├── MX_ADC1_Init
   │   ├── HAL_ADC_ConvCpltCallback
   │   └── vAdcTask 数据处理
   └── 使用方法

3. I2C 传感器读取（BME280/MPU6050）
   ├── BME280 驱动
   │   ├── BME280_Init 初始化
   │   ├── BME280_Read 读取数据
   │   └── 温湿度气压计算
   │
   ├── MPU6050 驱动
   │   ├── MPU6050_Init 初始化
   │   ├── MPU6050_ReadAll 读取全部
   │   └── 加速度计/陀螺仪数据
   │
   └── 使用方法
       ├── 队列传递数据
       └── 任务调度

4. printf 重定向
   ├── ITM_SendChar 实现
   │   ├── ITM 初始化
   │   ├── _write 重写
   │   └── 验证方法
   │
   └── UART 重定向
       ├── _write 重写
       └── HAL_UART_Transmit
```

**典型问题：** "给我一个完整的 UART DMA 驱动代码，我要把数据传到队列里"

---

### EXAMPLES/ADVANCED.md

**什么时候读这个？**

当你需要高级应用示例时：

- "多任务传感器融合怎么做？"
- "Tickless 低功耗模式怎么配置？"
- "STM32CubeMX 怎么生成 FreeRTOS 代码？"
- "CubeMX 生成的代码需要怎么修改？"

**包含内容：**

```
1. 多任务传感器融合
   ├── 系统架构
   │   ├── 传感器采集任务
   │   ├── 数据处理任务（滤波、融合）
   │   └── 数据发送任务
   │
   ├── 任务间通信
   │   ├── 原始数据队列
   │   ├── 融合数据队列
   │   └── I2C 互斥锁
   │
   ├── 互补滤波算法
   │   ├── 加速度计角度计算
   │   ├── 陀螺仪积分
   │   └── 融合实现
   │
   └── 完整代码
       ├── 任务定义
       ├── 队列创建
       └── 启动调度器

2. Tickless 低功耗模式
   ├── FreeRTOSConfig.h 配置
   │   ├── configUSE_TICKLESS_IDLE
   │   ├── configPRE_SLEEP_PROCESSING
   │   └── configPOST_SLEEP_PROCESSING
   │
   ├── 低功耗实现
   │   ├── vPreSleepProcessing
   │   ├── vPostSleepProcessing
   │   ├── 时钟恢复
   │   └── STOP 模式进入
   │
   └── 使用注意事项
       ├── 唤醒源配置
       ├── 唤醒时间
       └── 外设恢复

3. STM32CubeMX 配置说明
   ├── FreeRTOS 中间件配置
   │   ├── Middleware → FreeRTOS
   │   ├── Version 选择
   │   └── Config Parameters
   │
   ├── NVIC 配置
   │   ├── Priority Group 选择
   │   ├── PendSV/SysTick 优先级
   │   └── 外设中断优先级
   │
   ├── 外设 + DMA 配置
   │   ├── UART DMA 设置
   │   ├── ADC DMA 设置
   │   └── 中断使能
   │
   └── 生成的代码修改
       ├── MX_FREERTOS_Init 删除
       ├── HAL_Init 位置
       ├── 任务定义
       └── 堆栈大小调整
```

**典型问题：** "怎么配置 STM32CubeMX 生成 FreeRTOS 代码？"

---

## PATTERNS/ 目录：设计模式与陷阱

这个目录告诉你常见问题的解决方案。

---

### PATTERNS/DESIGN.md

**什么时候读这个？**

当你需要设计模式参考时：

- "生产者-消费者模式怎么实现？"
- "发布-订阅模式怎么做？"
- "状态机怎么实现？"
- "缓冲区池怎么管理？"

**包含内容：**

```
1. 生产者-消费者模式
   ├── 模式说明
   │   ├── 适用场景
   │   └── 架构图
   │
   ├── 单生产者单消费者
   │   ├── 队列实现
   │   ├── 任务定义
   │   └── 完整示例
   │
   ├── 多生产者多消费者
   │   ├── 多任务共享队列
   │   ├── 数据来源区分
   │   └── 完整示例
   │
   └── 变体
       ├── 带优先级的队列
       └── 带超时的获取

2. 发布-订阅模式
   ├── 模式说明
   │   ├── 适用场景
   │   └── 架构图
   │
   ├── 事件组实现
   │   ├── xEventGroupCreate
   │   ├── xEventGroupSetBits
   │   └── xEventGroupWaitBits
   │
   ├── 多条件触发
   │   ├── AND 逻辑（等待所有位）
   │   └── OR 逻辑（等待任一位）
   │
   └── 广播通知
       ├── 多任务等待同一事件
       └── 事件清除

3. 状态机实现
   ├── 模式说明
   │   ├── 有限状态机
   │   └── 适用场景
   │
   ├── 状态定义
   │   ├── enum 定义状态
   │   ├── 状态变量
   │   └── 状态转换表
   │
   ├── 事件定义
   │   ├── enum 定义事件
   │   └── 事件队列
   │
   ├── 状态处理函数
   │   ├── 状态处理表
   │   ├── 动作执行
   │   └── 状态转换
   │
   └── 完整示例
       ├── 状态机控制块
       ├── 状态处理函数
       └── 任务实现

4. 资源池管理
   ├── 模式说明
   │   ├── 固定大小缓冲区
   │   └── 内存碎片避免
   │
   ├── 缓冲区池实现
   │   ├── 静态数组
   │   ├── 使用标记
   │   └── 分配/释放函数
   │
   └── 内存池
       ├── pvPortMalloc 替代
       ├── 预分配内存
       └── 碎片避免
```

**典型问题：** "怎么实现一个生产者-消费者模式？"

---

### PATTERNS/INTERRUPT.md

**什么时候读这个？**

当你需要写中断代码时：

- "中断里能不能调用 xQueueSend？"
- "portYIELD_FROM_ISR 什么时候用？"
- "NVIC 优先级怎么配置？"
- "FromISR 和普通函数有什么区别？"

**包含内容：**

```
1. FromISR 函数使用规则
   ├── 为什么需要 FromISR
   │   ├── 普通函数不能在 ISR 中用
   │   ├── FromISR 不会阻塞
   │   └── 带优先级继承
   │
   ├── 哪些函数有 FromISR 版本
   │   ├── xQueueSendFromISR
   │   ├── xQueueReceiveFromISR
   │   ├── xSemaphoreGiveFromISR
   │   ├── xEventGroupSetBitsFromISR
   │   └── vTaskNotifyGiveFromISR
   │
   └── 正确用法
       ├── 不阻塞
       ├── xHigherPriorityTaskWoken 参数
       └── 返回值检查

2. portYIELD_FROM_ISR 详解
   ├── 什么时候需要调用
   │   ├── FromISR 返回 pdTRUE
   │   └── 需要唤醒高优先级任务
   │
   ├── 完整示例
   │   ├── DMA 传输完成中断
   │   ├── UART 接收中断
   │   └── 外部中断
   │
   └── 常见错误
       ├── 忘记调用
       ├── 错误参数
       └── 多次调用

3. NVIC 优先级配置
   ├── Cortex-M 优先级分组
   │   ├── NVIC_PRIORITYGROUP_4
   │   └── 优先级数值范围
   │
   ├── FreeRTOS 优先级要求
   │   ├── configKERNEL_INTERRUPT_PRIORITY
   │   ├── configMAX_SYSCALL_INTERRUPT_PRIORITY
   │   └── 优先级范围
   │
   └── 外设中断优先级设置
       ├── 定时器中断（5）
       ├── UART 中断（6）
       ├── DMA 中断（7）
       └── 外部中断（10）

4. 中断最佳实践
   ├── 最小化 ISR 执行时间
   │   ├── 只做必要操作
   │   ├── 其他工作交给任务
   │   └── 用通知/队列传递
   │
   ├── 用任务通知替代信号量
   │   ├── 更轻量
   │   ├── 更快
   │   └── 更少资源
   │
   └── 避免在 ISR 中做复杂处理
       ├── 不要调用会阻塞的函数
       ├── 不要做浮点运算
       └── 不要使用大内存
```

**典型问题：** "我在中断里调用 xQueueSend 为什么出错？"

---

### PATTERNS/TRAPS.md

**什么时候读这个？**

当你的程序出现奇怪问题时：

- "为什么高优先级任务反而很慢？"
- "程序跑一段时间就崩溃了"
- "感觉有死锁，怎么排查？"
- "堆栈溢出了怎么办？"

**包含内容：**

```
1. 优先级反转
   ├── 问题说明
   │   ├── 图解说明
   │   ├── 产生原因
   │   └── 危害
   │
   ├── 互斥锁优先级继承
   │   ├── xSemaphoreCreateMutex
   │   └── 自动提升优先级
   │
   ├── 解决方案
   │   ├── 使用互斥锁
   │   ├── 避免长时间持有锁
   │   └── 任务优先级设计
   │
   └── 完整示例
       ├── 有优先级反转的代码
       └── 修复后的代码

2. 堆栈溢出
   ├── 如何检测
   │   ├── configCHECK_FOR_STACK_OVERFLOW
   │   ├── vApplicationStackOverflowHook
   │   └── uxTaskGetStackHighWaterMark
   │
   ├── 如何预防
   │   ├── 合理设置堆栈大小
   │   ├── 避免大数组在栈上
   │   └── 定期检查堆栈使用
   │
   ├── 堆栈大小估算
   │   ├── 基础需求（128-256字）
   │   ├── 字符串处理（+64-128字）
   │   ├── 递归调用（+256字）
   │   └── 大数组（+数组大小）
   │
   └── 常见原因
       ├── 无限递归
       ├── 大局部变量
       └── 函数调用链太深

3. 死锁
   ├── 产生条件
   │   ├── 互斥
   │   ├── 持有并等待
   │   └── 循环等待
   │
   ├── 解决策略
   │   ├── 统一获取顺序
   │   ├── 使用单一互斥锁
   │   └── 超时获取
   │
   ├── 死锁示例
   │   ├── 两个互斥锁的死锁
   │   └── 任务间死锁
   │
   └── 死锁检测
       ├── 任务状态查看
       ├── 等待分析
       └── 预防措施

4. 资源泄漏
   ├── 内存泄漏
   │   ├── pvPortMalloc 不释放
   │   ├── 检测方法
   │   └── 修复方法
   │
   ├── 队列泄漏
   │   ├── xQueueCreate 不删除
   │   └── 修复方法
   │
   ├── 信号量泄漏
   │   ├── xSemaphoreCreateBinary 不删除
   │   └── 修复方法
   │
   └── 清理方法
       ├── 任务结束时清理
       ├── 使用全局资源
       └── 显式删除函数
```

**典型问题：** "为什么高优先级任务被阻塞了？程序里有优先级反转吗？"

---

## 如何让 AI 读取正确的文件

### 方法 1：自然语言描述（最推荐）

直接告诉 AI 你想做什么，AI 会根据 SKILL.md 中的规则自动判断读取哪些文件。

**示例对话：**

```
你：帮我写一个 UART DMA 驱动
AI：（自动读取 REFERENCE/HAL_DRIVERS.md 和 EXAMPLES/DRIVERS.md）
AI：好的，这是 UART DMA 驱动的完整代码...
```

```
你：我在中断里调用 xQueueSend 报错了
AI：（自动读取 PATTERNS/INTERRUPT.md）
AI：ISR 中应该用 xQueueSendFromISR，我来帮你修改代码...
```

```
你：程序有优先级反转的问题
AI：（自动读取 PATTERNS/TRAPS.md）
AI：优先级反转的解决方案是使用互斥锁...
```

---

### 方法 2：明确指定文件

如果你知道具体要读哪个文件，可以明确告诉 AI。

**示例对话：**

```
你：请读取 EXAMPLES/DRIVERS.md，帮我写一个 UART DMA 驱动
AI：（读取 EXAMPLES/DRIVERS.md）
AI：好的，根据 DRIVERS.md 中的 UART DMA 示例，这是完整代码...
```

```
你：请读取 PATTERNS/INTERRUPT.md，告诉我 FromISR 怎么用
AI：（读取 INTERRUPT.md）
AI：FromISR 函数使用规则如下...
```

---

### 方法 3：指定多个文件

**示例对话：**

```
你：请读取 REFERENCE/HAL_DRIVERS.md 和 PATTERNS/INTERRUPT.md，
   帮我写一个在中断里发送队列的 UART 驱动
AI：（读取两个文件）
AI：根据 HAL_DRIVERS.md 的 UART 驱动和 INTERRUPT.md 的中断规则...
```

---

## 快速查找表

**我想做...** → **告诉 AI 读这个**

| 需求 | 文件 |
|------|------|
| 创建任务 | EXAMPLES/BASIC.md |
| 用队列传数据 | EXAMPLES/BASIC.md |
| 用信号量同步 | EXAMPLES/BASIC.md |
| 用互斥锁保护资源 | EXAMPLES/BASIC.md |
| 多个任务协作 | PATTERNS/DESIGN.md |
| UART DMA 接收 | EXAMPLES/DRIVERS.md |
| ADC DMA 采集 | EXAMPLES/DRIVERS.md |
| I2C 传感器读取 | EXAMPLES/DRIVERS.md |
| printf 输出到串口 | REFERENCE/STD_LIBS.md |
| printf 输出到 ITM | REFERENCE/STD_LIBS.md |
| 中断里发队列 | PATTERNS/INTERRUPT.md |
| 配置 NVIC 优先级 | PATTERNS/INTERRUPT.md |
| 配置 SystemView | REFERENCE/DEBUG_TOOLS.md |
| 配置 TRACEalyzer | REFERENCE/DEBUG_TOOLS.md |
| 打印任务统计 | REFERENCE/DEBUG_TOOLS.md |
| 解决死锁 | PATTERNS/TRAPS.md |
| 解决堆栈溢出 | PATTERNS/TRAPS.md |
| 解决优先级反转 | PATTERNS/TRAPS.md |
| 低功耗模式 | EXAMPLES/ADVANCED.md |
| CubeMX 配置 | EXAMPLES/ADVANCED.md |
| 查 API 参数 | REFERENCE/FREERTOS_API.md |

---

## 目录结构总结

```
stm32-freertos/
├── SKILL.md              ← AI 唯一读取的主文件
├── USER_GUIDE.md         ← 你正在看的文件
├── REFERENCE/            ← API 参考
│   ├── FREERTOS_API.md   ← API 语法和参数
│   ├── STD_LIBS.md       ← 标准库集成
│   ├── HAL_DRIVERS.md    ← 外设驱动集成
│   └── DEBUG_TOOLS.md    ← 调试工具配置
├── EXAMPLES/             ← 代码示例
│   ├── BASIC.md          ← 基础组件示例
│   ├── DRIVERS.md        ← 外设驱动示例
│   └── ADVANCED.md       ← 高级应用示例
├── PATTERNS/             ← 设计模式
│   ├── DESIGN.md         ← 生产者-消费者等模式
│   ├── INTERRUPT.md      ← 中断最佳实践
│   └── TRAPS.md          ← 常见陷阱和解决
└── scripts/
    └── freertos_config_check.py
```

---

## 开始使用

1. **阅读本指南**，了解每个文件的用途
2. **当你有需求时**，用自然语言告诉 AI 你想做什么
3. **AI 会自动读取**相关的文档来回答你的问题
4. **如果 AI 回答不准确**，可以明确告诉 AI 读取特定文件

---

## 提示

- 如果你不确定该读哪个文件，直接描述你的问题即可，AI 会根据 SKILL.md 中的规则自动判断
- 如果你想让 AI 读特定文件，可以明确告诉它："请读取 EXAMPLES/DRIVERS.md"
- 多个文件可以用 "和" 连接："请读取 REFERENCE/HAL_DRIVERS.md 和 PATTERNS/INTERRUPT.md"
