"""Schema definitions for split command configuration."""

from pydantic import BaseModel, Field, RootModel, field_validator


class SheetConfig(BaseModel):
    """Configuration for a single sheet in the split command.

    Attributes:
        date_column: Name of the column containing date values
        date_format: Optional custom date format string (e.g., '%Y-%m-%d', '%d/%m/%Y')
        include: Whether to include this sheet in processing (default: True)
    """

    model_config = {"extra": "forbid"}

    date_column: str | None = Field(
        None, description="Name of the column containing date values"
    )
    date_format: str | None = Field(
        None, description="Custom date format string (e.g., '%Y-%m-%d', '%d/%m/%Y')"
    )
    include: bool = Field(
        True, description="Whether to include this sheet in processing"
    )

    @field_validator("date_column")
    @classmethod
    def validate_date_column(cls, v: str | None) -> str | None:
        """Validate date column name."""
        if v is not None and not v.strip():
            raise ValueError("Date column name cannot be empty or whitespace only")
        return v.strip() if v else v

    @field_validator("date_format")
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        """Validate date format string."""
        if v is not None:
            if not v.strip():
                raise ValueError("Date format cannot be empty or whitespace only")
            # Basic validation to ensure it contains % symbols for datetime formatting
            if "%" not in v:
                raise ValueError(
                    "Date format must contain datetime format specifiers (e.g., %Y, %m, %d)"
                )
        return v.strip() if v else v


class SplitSheetConfigSchema(RootModel[dict[str, SheetConfig]]):
    """Schema for the complete sheet configuration file.

    This is a mapping of sheet names to their individual configurations.
    Each sheet name maps to a SheetConfig object.
    """

    @field_validator("root")
    @classmethod
    def validate_sheet_configs(
        cls, v: dict[str, SheetConfig]
    ) -> dict[str, SheetConfig]:
        """Validate the complete sheet configuration."""
        if not v:
            raise ValueError("Sheet configuration cannot be empty")

        # Validate that at least one sheet is included
        included_sheets = [
            sheet_name for sheet_name, config in v.items() if config.include
        ]
        if not included_sheets:
            raise ValueError(
                "At least one sheet must be included (have 'include': true or omit the 'include' field)"
            )

        # Validate sheet names
        for sheet_name in v:
            if not sheet_name.strip():
                raise ValueError("Sheet names cannot be empty or whitespace only")

        return v

    def __getitem__(self, key: str) -> SheetConfig:
        """Allow dictionary-style access to sheet configurations."""
        return self.root[key]

    def items(self):
        """Return sheet name and config pairs."""
        return self.root.items()

    def keys(self):
        """Return sheet names."""
        return self.root.keys()

    def values(self):
        """Return sheet configurations."""
        return self.root.values()
