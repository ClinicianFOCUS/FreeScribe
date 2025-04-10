"""
Example usage of the Intent Action Manager.

This module demonstrates how to initialize and use the Intent Action Manager
to process text, recognize intents, and execute corresponding actions.
"""

import os
import logging
from pathlib import Path
from services.intent_actions.manager import IntentActionManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(lineno)s:%(funcName)s:%(filename)s | %(message)s '
)
logger = logging.getLogger(__name__)

def main():
    """
    Demonstrate basic usage of the Intent Action Manager.
    
    This function shows how to:
    1. Initialize the IntentActionManager
    2. Process various example texts
    3. Handle and display the results
    """
    try:
        # Initialize the manager with required parameters
        maps_dir = Path("./maps_output")
        maps_dir.mkdir(exist_ok=True)
        logger.info(f"Created maps directory at: {maps_dir.absolute()}")
        
        # Replace with your actual API key or get from settings
        google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        
        # Create the manager instance
        manager = IntentActionManager(maps_dir, google_maps_api_key)
        logger.info("IntentActionManager initialized successfully")
        
        # Example texts to process
        example_texts = [
            "I need to get to Grand River Hospital for my appointment at 2PM",
            "Where is Grand River Hospital?",
            "I need directions to the St. Mary’s General Hospital",
            "Can you show me how to get to Grand River Hospital Emergency Room?",
            "Where is the main entrance of the hospital?",
            "I need to find St. Mary's Regional Cardiac Care Centre",
            "Show me the way to the cafeteria",
            "This is a normal sentence without any intent"  # Control case
        ]
        
        # Process each example text
        for text in example_texts:
            logger.info(f"\nProcessing text: {text}")
            
            # Get intents directly from recognizer for debugging
            intents = manager.intent_recognizer.recognize_intent(text)
            logger.info(f"Recognized intents: {intents}")
            
            # Process text through manager
            results = manager.process_text(text)
            
            # Display results
            if results:
                for result in results:
                    print("-" * 50)
                    print(f"Action: {result['display_name']}")
                    print(f"Message: {result['message']}")
                    if result['data']:
                        print(f"Data: {result['data']}")
                    if result['ui']:
                        print(f"UI Configuration: {result['ui']}")
            else:
                logger.info("No intents or actions were triggered for this text")
            print("-" * 50)
    
    except Exception as e:
        logger.exception("Error occurred while running the example")
        raise

def run_single_example(text: str, manager: IntentActionManager) -> None:
    """
    Process a single example text and display results.
    
    :param text: Text to process
    :param manager: Initialized IntentActionManager instance
    """
    try:
        print(f"\nProcessing: {text}")
        results = manager.process_text(text)
        
        if not results:
            print("No actions triggered")
            return
            
        for result in results:
            print(f"Action: {result['display_name']}")
            print(f"Result: {result['message']}")
            
    except Exception as e:
        logger.exception(f"Error processing text: {text}")

if __name__ == "__main__":
    main() 