### 可调用工具：
1.  langchain_and_langgraph_doc：在写涉及到langchain和langgraph相关技术栈的代码编写时，时请先调用langchain_and_langgraph_doc模块查找最新的框架文档了解该如何写langgraph项目搭建agent

2.  context7：在构建需要用到币安binance api时，请调用context7工具查询相关技术文档与资料 

注意：
调用Read工具了。路径格式是 D:\langgraph\（Windows格式）。要用windows格式
调用bash工具时，请使用python命令而不是python3执行，例如Bash(python test_hotel_recommendation_fixed.py)

你在输出答案时，请不要使用cat << 'EOF'，这些内容我看不到我需要点开才能看到很不方便，你直接输出出来即可   

### 编码注意事项：

1.  **编码时一定不要使用所有的emoji和特殊字符，一定不要使用emoji字符！！！

###代码执行注意事项：
2.  **所有代码执行都是在当前venv虚拟环境下执行

### 自我测试：
1.  **每实现完成一个功能模块请进行自我测试
2.  **当需要配置环境变量时，请告诉我，我去配置到env环境，并且你需要创建env.example文件
3.  **每次自测，你需要看当前测试文件功能是否和D:\AI_deepseek_trader\crypto_trader\core\event_system.py有关，这个event_system.py文件是主代码启动文件，如果有关你要用event_system.py内的函数进行测试效果