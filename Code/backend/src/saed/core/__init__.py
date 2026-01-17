"""SAED Core - 核心功能模块"""

# Silence langchain/pydantic V1 warning on Python 3.14+ until upstream fixes.
import warnings

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=r"Core Pydantic V1 functionality isn't compatible with Python 3.14",
)
