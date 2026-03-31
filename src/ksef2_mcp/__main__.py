import warnings

from beartype.roar import BeartypeDecorHintPep585DeprecationWarning


warnings.filterwarnings(
    "ignore",
    category=BeartypeDecorHintPep585DeprecationWarning,
)

from ksef2_mcp.server import main

if __name__ == "__main__":
    main()
