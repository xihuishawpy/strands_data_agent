"""
智能体基类
为所有专用智能体提供通用功能
"""

import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from openai import OpenAI
from ..config import config

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(self, name: str, system_prompt: str, model_name: Optional[str] = None):
        """
        初始化智能体
        
        Args:
            name: 智能体名称
            system_prompt: 系统提示
            model_name: 使用的模型名称，如果为None则使用默认模型
        """
        self.name = name
        self.system_prompt = system_prompt
        self.model_name = model_name or config.llm.model_name
        
        # 创建OpenAI客户端实例
        self.client = OpenAI(
            api_key=config.llm.api_key,
            base_url=config.llm.base_url
        )
        
        logger.info(f"智能体 {self.name} 初始化完成，使用模型: {self.model_name}")
    
    def run(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        运行智能体
        
        Args:
            query: 查询内容
            context: 上下文信息
            
        Returns:
            str: 智能体响应
        """
        try:
            # 构建完整的提示
            user_prompt = self._build_prompt(query, context)
            
            # 调用OpenAI兼容的API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content
            logger.debug(f"智能体 {self.name} 响应: {result}")
            return result
            
        except Exception as e:
            logger.error(f"智能体 {self.name} 运行失败: {str(e)}")
            return f"智能体执行失败: {str(e)}"
    
    @abstractmethod
    def _build_prompt(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        构建完整的提示
        
        Args:
            query: 用户查询
            context: 上下文信息
            
        Returns:
            str: 完整的提示
        """
        pass
    
    def set_context(self, context: Dict[str, Any]):
        """设置上下文信息"""
        self.context = context
    
    def validate_input(self, query: str) -> tuple[bool, str]:
        """
        验证输入
        
        Args:
            query: 输入查询
            
        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        if not query or not query.strip():
            return False, "查询不能为空"
        
        if len(query) > 10000:  # 限制输入长度
            return False, "查询内容过长"
        
        return True, ""

class ChatAgent(BaseAgent):
    """通用对话智能体"""
    
    def __init__(self, name: str = "ChatAgent", model_name: Optional[str] = None):
        system_prompt = """
        你是一个专业的AI助手，能够理解和回答各种问题。
        请用中文回复，保持回答准确、有用、简洁。
        """
        super().__init__(name, system_prompt, model_name)
    
    def _build_prompt(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """构建对话提示"""
        prompt_parts = []
        
        if context:
            if "conversation_history" in context:
                prompt_parts.append("对话历史:")
                for msg in context["conversation_history"][-5:]:  # 只保留最近5条
                    prompt_parts.append(f"{msg['role']}: {msg['content']}")
                prompt_parts.append("")
            
            if "additional_info" in context:
                prompt_parts.append(f"附加信息: {context['additional_info']}")
                prompt_parts.append("")
        
        prompt_parts.append(f"用户问题: {query}")
        
        return "\n".join(prompt_parts) 