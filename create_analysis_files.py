#!/usr/bin/env python3
"""
Script to create or replace the analysis mode file for each customer.
This ensures that each customer template has a proper modes/analysis.txt file.
"""

import os
import sys

# List of customers to process
CUSTOMERS = [
    "deskmate",
    "duogaming",
    "fictra",
    "fictra-foundation",
    "fictra-participants",
    "fictra-sovereign",
    "harmonyprotocol",
    "kinkong",
    "kinos",
    "konginvest",
    "marketingmesh",
    "sottowelcome",
    "stride",
    "stridecoaching",
    "strideentrepreneur",
    "strideexecutive",
    "stridewomen",
    "therapykin",
    "therapykinathletes",
    "therapykincrypto",
    "therapykinexecutives",
    "therapykinherosjourney",
    "therapykinsexologist",
    "therapykinwelcome"
]

# Standard content for the analysis.txt file
ANALYSIS_CONTENT = """# Analysis Mode: Informative Responses Without Memorization

In this mode, you provide information and analysis without memorizing the content of the exchange. This mode is designed for:

1. Answering administrative or debugging questions
2. Providing explanations about your internal functioning
3. Assisting with moderation and supervision
4. Allowing exploratory interactions without impact on your long-term memory

## Specific Guidelines

When operating in this mode:

- Respond with precision and honesty to questions asked
- Explain your reasoning and internal processes if requested
- Provide complete information about your configuration and capabilities
- Do not initiate the creation or modification of memory files
- Do not consider this conversation as something that should influence your future interactions

## Practical Applications

This mode is particularly useful for:
- System administrators checking your configuration
- Moderators evaluating your behavior
- Users wanting to understand your capabilities without modifying your behavior
- Testing and debugging your functioning

Your goal is to provide useful and accurate information while maintaining a clear separation between this interaction and your long-term memory.
"""

def main():
    # Get the base directory (assuming the script is in the project root)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    customers_dir = os.path.join(base_dir, "customers")
    
    print(f"Using customers directory: {customers_dir}")
    
    # Check if customers directory exists
    if not os.path.exists(customers_dir):
        print(f"Error: Customers directory not found at {customers_dir}")
        sys.exit(1)
    
    # Process each customer
    for customer in CUSTOMERS:
        print(f"Processing customer: {customer}")
        
        # Path to the customer template directory
        template_dir = os.path.join(customers_dir, customer, "template")
        print(f"  Template directory: {template_dir}")
        
        # Check if template directory exists
        if not os.path.exists(template_dir):
            print(f"  Warning: Template directory not found for {customer}, skipping")
            continue
        
        # Path to the modes directory
        modes_dir = os.path.join(template_dir, "modes")
        print(f"  Modes directory: {modes_dir}")
        
        # Create modes directory if it doesn't exist
        if not os.path.exists(modes_dir):
            print(f"  Creating modes directory for {customer}")
            os.makedirs(modes_dir, exist_ok=True)
        
        # Path to the analysis.txt file
        analysis_file = os.path.join(modes_dir, "analysis.txt")
        print(f"  Analysis file: {analysis_file}")
        
        # Create or replace the analysis.txt file
        try:
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write(ANALYSIS_CONTENT)
            print(f"  Created/updated analysis.txt for {customer}")
            
            # Verify the file was created
            if os.path.exists(analysis_file):
                file_size = os.path.getsize(analysis_file)
                print(f"  Verified file exists, size: {file_size} bytes")
            else:
                print(f"  Error: File not found after creation attempt")
        except Exception as e:
            print(f"  Error creating analysis.txt for {customer}: {str(e)}")
    
    print("\nDone! Analysis mode files have been created or updated for all customers.")

if __name__ == "__main__":
    main()
