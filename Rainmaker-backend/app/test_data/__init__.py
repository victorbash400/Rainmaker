"""
Test data for enrichment agent validation and testing.
"""

from .mock_prospects import (
    MOCK_PROSPECTS,
    EXPECTED_INSIGHTS,
    get_mock_prospect_by_name,
    get_all_mock_prospects,
    get_expected_insights_for_prospect
)

__all__ = [
    "MOCK_PROSPECTS",
    "EXPECTED_INSIGHTS", 
    "get_mock_prospect_by_name",
    "get_all_mock_prospects",
    "get_expected_insights_for_prospect"
]