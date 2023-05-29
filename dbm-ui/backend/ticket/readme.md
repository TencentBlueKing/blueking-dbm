新增一个单据类型仅需在 backend/ticket/builders 下新增一个文件即可，

- TicketSerializer # 单据序列化器
  - validate # 用于校验前端参数
  - to_representation # 用户侧（前端）展示所需的数据


- ItsmParamBuilder # 可选，当没有审批流程时可以不定义
  - format # 格式化请求ITSM的参数，增强单据可读性


- FlowParamBuilder # 构建任务流程运行所需的参数
  - format_ticket_data # 将 ticket.details 转化为流程实际运行所需要的参数（默认直接使用 ticket.details 的数据）


- TicketFlowBuilder # 用于构建单据流程
  - init_ticket_flows # 构建单据流程并初始化参数

其中，TicketFlowBuilder 需要使用以下装饰器，以达到自动注册的目的
@builders.BuilderFactory.register(TicketType.XXX)