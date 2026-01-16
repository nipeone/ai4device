class WorkflowEngine:
    def __init__(self):
        self.state_machine = {
            'PENDING': self.start_workflow,
            'WAITING_MATERIAL': self.wait_for_confirm,
            'BATCHING': self.execute_batching,
            'WAITING_SEAL': self.wait_for_confirm,
            'SEALING': self.execute_sealing,
            # ... 其他状态
        }
    
    async def execute_task(self, task_id):
        task = await self.get_task(task_id)
        handler = self.state_machine.get(task.status)
        
        if handler:
            await handler(task)
    
    async def execute_batching(self, task):
        # 调用配料设备API
        response = await batching_device.start(task.materials)
        
        if response.success:
            task.status = 'WAITING_SEAL'
            await self.notify_operator(task, "配料完成,请将样品放入熔封设备")
        else:
            task.status = 'FAILED'
    
    async def confirm_step(self, task_id, step, operator):
        task = await self.get_task(task_id)
        
        if task.status == step:
            # 状态转换
            next_status = self.get_next_status(step)
            task.status = next_status
            await self.save_task(task)
            
            # 继续执行下一步
            await self.execute_task(task_id)