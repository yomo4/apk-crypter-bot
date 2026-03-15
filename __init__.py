"""
Services модуль для CRUPTOANON
Включает криптографию, защиту, обфускацию и построение APK
"""

from .apk_crypter import APKCrypter
from .obfuscator import ObfuscationManager, CodeObfuscator
from .protection import (
    ProtectionManager,
    SecurityToken,
    IntegrityChecker,
    RateLimiter,
    AntiTamperingMonitor,
    ExecutionEnvironmentValidator,
    ProtectionException
)
from .advanced_protection import (
    AndroidEnvironmentDetector,
    AntiAnalysisProtection,
    ProtectionDecorator,
    DetectionType
)
from .npmanager import (
    NPManager,
    NPMPackage,
    NPManagerFactory,
    NPManagerBatchProcessor,
    TechFrameworkMasker,
    AndroidSystemMasker,
    MythicalName,
    SystemServiceMask
)
from .full_protector import (
    FullAPKProtector,
    APKProtectionPipeline
)
from .stub_builder import StubBuilder

__all__ = [
    "APKCrypter",
    "ObfuscationManager",
    "CodeObfuscator",
    "ProtectionManager",
    "SecurityToken",
    "IntegrityChecker",
    "RateLimiter",
    "AntiTamperingMonitor",
    "ExecutionEnvironmentValidator",
    "ProtectionException",
    "AndroidEnvironmentDetector",
    "AntiAnalysisProtection",
    "ProtectionDecorator",
    "DetectionType",
    "NPManager",
    "NPMPackage",
    "NPManagerFactory",
    "NPManagerBatchProcessor",
    "TechFrameworkMasker",
    "AndroidSystemMasker",
    "MythicalName",
    "SystemServiceMask",
    "FullAPKProtector",
    "APKProtectionPipeline",
    "StubBuilder",
]
