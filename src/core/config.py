    print("SwarmIA Configuration")
    print("="*60)
    
    print("\n📁 Paths:")
    print(f"  Base Directory: {config.BASE_DIR}")
    print(f"  Config Directory: {config.CONFIG_DIR}")
    print(f"  Logs Directory: {config.LOGS_DIR}")
    print(f"  Data Directory: {config.DATA_DIR}")
    
    print("\n🌐 Server:")
    print(f"  Host: {config.SERVER_HOST}")
    print(f"  Port: {config.SERVER_PORT}")
    print(f"  Workers: {config.SERVER_WORKERS}")
    
    print("\n🤖 AI:")
    print(f"  Default Provider: {config.AI_DEFAULT_PROVIDER}")
    print(f"  Max Tokens: {config.AI_MAX_TOKENS}")
    print(f"  Temperature: {config.AI_TEMPERATURE}")
    
    print("\n🔐 Security:")
    print(f"  JWT Algorithm: {config.JWT_ALGORITHM}")
    print(f"  JWT Expire Minutes: {config.JWT_EXPIRE_MINUTES}")
    
    print("\n📊 System Info:")
    print(f"  Local IP: {config.get_local_ip()}")
    print(f"  Public IP: {config.get_public_ip()}")
    
    print("\n" + "="*60)
    
    # Validate configuration
    if config.validate():
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration has errors")
    
    # Save configuration
    if config.save():
        print("💾 Configuration saved to file")