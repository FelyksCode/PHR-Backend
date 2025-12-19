"""
Simple test script to validate Fitbit integration setup
Run this to check if everything is configured correctly
"""
import os
from dotenv import load_dotenv

load_dotenv()

def check_environment():
    """Check if all required environment variables are set"""
    print("=" * 60)
    print("FITBIT INTEGRATION - ENVIRONMENT CHECK")
    print("=" * 60)
    
    required_vars = {
        "FITBIT_CLIENT_ID": "Fitbit OAuth Client ID",
        "FITBIT_CLIENT_SECRET": "Fitbit OAuth Client Secret",
        "FITBIT_REDIRECT_URI": "Fitbit OAuth Redirect URI",
        "ENCRYPTION_KEY": "Token Encryption Key",
        "DATABASE_URL": "Database URL",
        "FHIR_BASE_URL": "FHIR Server URL",
        "SECRET_KEY": "JWT Secret Key"
    }
    
    all_set = True
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value and value.strip():
            print(f"✅ {description}: {'*' * 10} (set)")
        else:
            print(f"❌ {description}: NOT SET")
            all_set = False
    
    print("\n" + "=" * 60)
    
    if all_set:
        print("✅ All environment variables are configured!")
    else:
        print("❌ Some environment variables are missing.")
        print("\nTo fix:")
        print("1. Copy .env.example to .env")
        print("2. Fill in the missing values")
        print("3. Generate encryption key:")
        print("   python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
    
    return all_set

def check_encryption_key():
    """Validate encryption key format"""
    print("\n" + "=" * 60)
    print("ENCRYPTION KEY VALIDATION")
    print("=" * 60)
    
    try:
        from app.services.encryption import token_encryption
        test_data = "test_token_123"
        encrypted = token_encryption.encrypt(test_data)
        decrypted = token_encryption.decrypt(encrypted)
        
        if decrypted == test_data:
            print("✅ Encryption key is valid and working correctly")
            return True
        else:
            print("❌ Encryption/decryption failed - data mismatch")
            return False
    except ValueError as e:
        print(f"❌ Encryption key error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def check_database():
    """Check if database is accessible"""
    print("\n" + "=" * 60)
    print("DATABASE CHECK")
    print("=" * 60)
    
    try:
        from app.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def check_models():
    """Check if models can be imported"""
    print("\n" + "=" * 60)
    print("MODEL IMPORTS CHECK")
    print("=" * 60)
    
    try:
        from app.models.vendor_integration import VendorIntegration, OAuthToken
        print("✅ VendorIntegration model imported")
        print("✅ OAuthToken model imported")
        return True
    except Exception as e:
        print(f"❌ Model import failed: {str(e)}")
        return False

def check_services():
    """Check if services can be imported"""
    print("\n" + "=" * 60)
    print("SERVICE IMPORTS CHECK")
    print("=" * 60)
    
    services = [
        ("app.services.encryption", "token_encryption"),
        ("app.services.vendor_integration_service", "vendor_integration_service"),
        ("app.services.oauth_token_service", "oauth_token_service"),
        ("app.services.fitbit_service", "fitbit_service"),
        ("app.services.fhir_mapper", "fhir_mapper"),
        ("app.services.sync_service", "sync_service")
    ]
    
    all_imported = True
    for module_path, service_name in services:
        try:
            module = __import__(module_path, fromlist=[service_name])
            getattr(module, service_name)
            print(f"✅ {service_name} imported successfully")
        except Exception as e:
            print(f"❌ {service_name} import failed: {str(e)}")
            all_imported = False
    
    return all_imported

def check_routers():
    """Check if routers can be imported"""
    print("\n" + "=" * 60)
    print("ROUTER IMPORTS CHECK")
    print("=" * 60)
    
    routers = [
        ("app.routers.integrations", "integrations_router"),
        ("app.routers.fitbit", "fitbit_router"),
        ("app.routers.health", "health_router")
    ]
    
    all_imported = True
    for module_path, router_name in routers:
        try:
            module = __import__(module_path, fromlist=["router"])
            print(f"✅ {router_name} imported successfully")
        except Exception as e:
            print(f"❌ {router_name} import failed: {str(e)}")
            all_imported = False
    
    return all_imported

def main():
    """Run all checks"""
    print("\n" + "=" * 60)
    print("FITBIT INTEGRATION - SETUP VALIDATION")
    print("=" * 60 + "\n")
    
    results = {
        "Environment Variables": check_environment(),
        "Encryption Key": check_encryption_key(),
        "Database Connection": check_database(),
        "Model Imports": check_models(),
        "Service Imports": check_services(),
        "Router Imports": check_routers()
    }
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED!")
        print("\nYou're ready to start the server:")
        print("  uvicorn app.main:app --reload")
        print("\nThen visit:")
        print("  http://localhost:8000/docs")
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease fix the issues above before starting the server.")
        print("\nFor help, see:")
        print("  - docs/FITBIT_QUICKSTART.md")
        print("  - docs/FITBIT_INTEGRATION.md")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
