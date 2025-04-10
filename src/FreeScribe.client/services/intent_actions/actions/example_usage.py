"""
Example usage of PrintMapAction to handle intents and display maps using Google Maps API.

This example demonstrates how to:
1. Initialize the PrintMapAction with Google Maps API key
2. Check if it can handle an intent
3. Execute the action with different intents
4. Generate and save maps using Google Maps API
"""

import logging
from pathlib import Path
from typing import Dict, Any
import os

from .print_map import PrintMapAction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    # add line number, module name
    format='%(asctime)s - %(name)s - %(levelname)s - %(lineno)s:%(funcName)s:%(filename)s | %(message)s '
)
logger = logging.getLogger(__name__)

def simulate_intent_handling(action: PrintMapAction, intent_name: str, metadata: Dict[str, Any]) -> None:
    """
    Simulate handling an intent with the given action.
    
    :param action: The action instance to use
    :param intent_name: Name of the intent to handle
    :param metadata: Additional data for the intent
    """
    logger.info(f"Processing intent: {intent_name}")
    logger.info(f"Intent metadata: {metadata}")
    
    # Check if action can handle this intent
    can_handle = action.can_handle_intent(intent_name, metadata)
    if not can_handle:
        logger.warning(f"Action {action.action_id} cannot handle intent {intent_name}")
        return
        
    # Execute the action
    result = action.execute(intent_name, metadata)
    
    # Log the results
    if result.success:
        logger.info(f"Action succeeded: {result.message}")
        if result.data:
            logger.info(f"Additional data: {result.data}")
            # Log map information if available
            if "map_image_path" in result.data.get("additional_info", {}):
                logger.info(f"Map saved to: {result.data['additional_info']['map_image_path']}")
            if "google_maps_url" in result.data.get("additional_info", {}):
                logger.info(f"Google Maps URL: {result.data['additional_info']['google_maps_url']}")
    else:
        logger.error(f"Action failed: {result.message}")

def main():
    """Run example intent handling scenarios."""
    # Get Google Maps API key from environment variable
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error("GOOGLE_MAPS_API_KEY environment variable not set")
        return
        
    # Initialize the action with a maps directory and API key
    maps_dir = Path("./hospital_maps")
    action = PrintMapAction(maps_dir, api_key)
    
    # Example 1: Show map for radiology
    logger.info("\n=== Example 1: Show map for radiology ===")
    simulate_intent_handling(
        action,
        intent_name="show_map",
        metadata={"destination": "radiology"}
    )
    
    # Example 2: Get directions to emergency
    logger.info("\n=== Example 2: Get directions to emergency ===")
    simulate_intent_handling(
        action,
        intent_name="get_directions",
        metadata={"destination": "emergency"}
    )
    
    # Example 3: Find location of cafeteria
    logger.info("\n=== Example 3: Find location of cafeteria ===")
    simulate_intent_handling(
        action,
        intent_name="find_location",
        metadata={"destination": "cafeteria"}
    )
    
    # Example 4: Invalid intent
    logger.info("\n=== Example 4: Invalid intent ===")
    simulate_intent_handling(
        action,
        intent_name="invalid_intent",
        metadata={"destination": "radiology"}
    )
    
    # Example 5: Unknown location
    logger.info("\n=== Example 5: Unknown location ===")
    simulate_intent_handling(
        action,
        intent_name="show_map",
        metadata={"destination": "unknown_place"}
    )

if __name__ == "__main__":
    main() 