"""
Action System for Autonomous Realms

This module handles the available actions, their requirements, and outcomes
based on terrain, era, and colony development.
"""

import random
import json
import os
from pathlib import Path

class ActionSystem:
    """
    Manages actions available to colonists based on terrain, technology level,
    and available resources.
    """
    
    def __init__(self, data_path="data/actions", terrain_system=None):
        """
        Initialize the action system with configuration data.
        
        Args:
            data_path: Path to action data files
            terrain_system: Reference to the terrain system
        """
        self.data_path = data_path
        self.terrain_system = terrain_system
        self.action_codes = self._load_json("action_codes.json")
        self.terrain_actions = self._load_json("terrain_actions.json")
        self.progression_paths = self._load_json("progression_paths.json")
        
        self.current_era = "stone_age"
        self.available_tools = set()
        self.available_technologies = set()
        self.completed_actions = set()
        self.observations = {}
        self.resources = {}
        
    def _load_json(self, filename):
        """Load JSON data from file."""
        file_path = os.path.join(self.data_path, filename)
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def get_available_actions(self, terrain_code, group_size=1):
        """
        Determine available actions based on terrain and colony development.
        
        Args:
            terrain_code: 5-digit terrain code
            group_size: Number of colonists available for the action
            
        Returns:
            List of available action codes
        """
        if not self.terrain_system:
            raise ValueError("Terrain system reference is required")
            
        # Get biome type from terrain code
        biome_type = self.terrain_system.find_biome_type(terrain_code)
        
        # Get special feature from terrain code
        special_feature = terrain_code[4] if len(terrain_code) > 4 and terrain_code[4] else ""
        
        # Get actions available for this biome in the current era
        biome_actions = set()
        if biome_type in self.terrain_actions["terrain_action_mappings"]:
            if self.current_era in self.terrain_actions["terrain_action_mappings"][biome_type]:
                biome_actions.update(self.terrain_actions["terrain_action_mappings"][biome_type][self.current_era])
        
        # Add actions available for special features
        if special_feature and special_feature in self.terrain_actions["special_feature_actions"]:
            if self.current_era in self.terrain_actions["special_feature_actions"][special_feature]:
                biome_actions.update(self.terrain_actions["special_feature_actions"][special_feature][self.current_era])
        
        # Filter actions based on requirements
        available_actions = []
        
        for action_code in biome_actions:
            # Get action details
            action_data = self._get_action_data(action_code)
            if not action_data:
                continue
                
            # Check if action meets all requirements
            if self._meets_requirements(action_data, terrain_code, group_size):
                available_actions.append(action_code)
        
        return available_actions
    
    def _get_action_data(self, action_code):
        """Get action data from the appropriate category based on era."""
        if self.current_era == "stone_age":
            if action_code in self.action_codes["action_codes"]:
                return self.action_codes["action_codes"][action_code]
        elif self.current_era == "bronze_age":
            if action_code in self.action_codes["bronze_age_actions"]:
                return self.action_codes["bronze_age_actions"][action_code]
            elif action_code in self.action_codes["action_codes"]:
                return self.action_codes["action_codes"][action_code]
        elif self.current_era == "iron_age":
            if action_code in self.action_codes["iron_age_actions"]:
                return self.action_codes["iron_age_actions"][action_code]
            elif action_code in self.action_codes["action_codes"]:
                return self.action_codes["action_codes"][action_code]
        
        return None
    
    def _meets_requirements(self, action_data, terrain_code, group_size):
        """Check if all requirements for an action are met."""
        requirements = action_data.get("requirements", {})
        
        # Check era requirement
        if "era" in requirements and requirements["era"] != self.current_era:
            return False
        
        # Check terrain features requirement
        if "terrain_features" in requirements:
            special_feature = terrain_code[4] if len(terrain_code) > 4 and terrain_code[4] else ""
            if special_feature not in requirements["terrain_features"]:
                return False
        
        # Check resource requirements
        if "resources" in requirements:
            for resource in requirements["resources"]:
                if resource not in self.resources:
                    return False
        
        # Check tool requirements
        if "tools" in requirements:
            required_tools = set(requirements["tools"])
            if not required_tools.issubset(self.available_tools):
                return False
        
        # Check knowledge requirements
        if "knowledge" in requirements:
            required_knowledge = set(requirements["knowledge"])
            if not required_knowledge.issubset(self.available_technologies):
                return False
        
        # Check group size requirement
        if "group_size" in requirements and group_size < requirements["group_size"]:
            return False
        
        return True
    
    def perform_action(self, action_code, terrain_code, colonists):
        """
        Perform an action and determine the outcome.
        
        Args:
            action_code: Code of the action to perform
            terrain_code: 5-digit terrain code where the action is performed
            colonists: List of colonist objects performing the action
            
        Returns:
            Dictionary containing the outcome of the action
        """
        # Get action data
        action_data = self._get_action_data(action_code)
        if not action_data:
            return {"success": False, "message": f"Unknown action: {action_code}"}
        
        # Check if action is available
        group_size = len(colonists)
        if not self._meets_requirements(action_data, terrain_code, group_size):
            return {"success": False, "message": "Requirements not met for this action"}
        
        # Calculate base success chance
        success_chance = 0.7  # Base success rate
        
        # Adjust based on terrain suitability
        if self.terrain_system:
            # Different actions have different terrain suitability metrics
            suitability_type = self._get_suitability_type(action_code)
            terrain_suitability = self.terrain_system.analyze_terrain_suitability(terrain_code, suitability_type)
            success_chance += (terrain_suitability - 0.5) * 0.4  # Adjust by up to ±20% based on terrain
        
        # Adjust based on colonist skills (simplified)
        skill_bonus = 0.05 * min(group_size, 5)  # Up to +25% for 5 or more colonists
        success_chance += skill_bonus
        
        # Determine if action succeeds
        success = random.random() < success_chance
        
        # Record that this action was attempted
        self.completed_actions.add(action_code)
        
        # Process outcomes
        result = {
            "success": success,
            "action_name": action_data["name"],
            "message": f"{'Successfully completed' if success else 'Failed to complete'} {action_data['name']}",
            "resources_gained": {},
            "knowledge_gained": 0,
            "risks_occurred": []
        }
        
        if success:
            # Process successful outcomes
            outcomes = action_data.get("outcomes", {})
            
            # Resource gains
            for resource, amount in outcomes.items():
                if resource == "knowledge" or resource == "knowledge_sharing":
                    knowledge_value = self._convert_text_amount_to_value(amount)
                    result["knowledge_gained"] = knowledge_value
                elif resource == "discovery_chance":
                    # Handle potential discoveries
                    discovery_chance = self._convert_text_amount_to_value(amount) * 0.1  # Scale to reasonable percentage
                    if random.random() < discovery_chance:
                        discovery = self._generate_discovery(action_code, terrain_code)
                        if discovery:
                            result["discovery"] = discovery
                elif resource == "future_food":
                    # For agriculture actions that produce food later
                    future_amount = self._convert_text_amount_to_value(amount)
                    result["future_resources"] = {"food": future_amount}
                else:
                    # Regular resources
                    resource_amount = self._convert_text_amount_to_value(amount)
                    # Adjust based on terrain
                    if self.terrain_system and resource in ["wood", "stone", "copper", "iron"]:
                        available_resources = self.terrain_system.get_available_resources(terrain_code)
                        if resource in available_resources:
                            resource_amount *= (0.5 + available_resources[resource])
                    
                    result["resources_gained"][resource] = resource_amount
                    # Update colony resources
                    if resource in self.resources:
                        self.resources[resource] += resource_amount
                    else:
                        self.resources[resource] = resource_amount
        
        # Process risks regardless of success
        risks = action_data.get("risks", {})
        for risk, probability in risks.items():
            risk_chance = self._convert_text_amount_to_value(probability) * 0.1  # Scale to reasonable percentage
            if random.random() < risk_chance:
                result["risks_occurred"].append(risk)
        
        # Check for observations and potential technology unlocks
        self._process_observations(action_code, terrain_code)
        self._check_technology_unlocks()
        self._check_tool_unlocks()
        self._check_era_advancement()
        
        return result
    
    def _get_suitability_type(self, action_code):
        """Determine the appropriate terrain suitability type for an action."""
        category = action_code.split("-")[0]
        
        # Map action categories to suitability types
        category_mapping = {
            "G": "agriculture_potential",  # Gathering
            "H": "agriculture_potential",  # Hunting
            "F": "agriculture_potential",  # Fishing
            "M": "resource_potential",     # Mining
            "W": "agriculture_potential",  # Woodworking
            "A": "agriculture_potential",  # Agriculture
            "C": "settlement_suitability", # Construction
            "T": "settlement_suitability", # Tool-making
            "S": "settlement_suitability", # Social
            "R": "settlement_suitability", # Research
            "E": "exploration_potential",  # Exploration
            "D": "defense_potential",      # Defense
            "P": "settlement_suitability", # Production
            "V": "settlement_suitability"  # Advanced
        }
        
        return category_mapping.get(category, "settlement_suitability")
    
    def _convert_text_amount_to_value(self, text_amount):
        """Convert text-based amount descriptions to numeric values."""
        amount_mapping = {
            "very_low": 1,
            "low": 2,
            "medium": 5,
            "high": 10,
            "very_high": 15,
            "extreme": 20
        }
        
        return amount_mapping.get(text_amount, 0)
    
    def _generate_discovery(self, action_code, terrain_code):
        """Generate a random discovery based on action and terrain."""
        # List of possible discoveries based on action category
        category = action_code.split("-")[0]
        
        discoveries = {
            "G": ["edible_plant_variety", "medicinal_herb", "natural_dye"],
            "H": ["animal_behavior_pattern", "tracking_technique", "new_game_species"],
            "F": ["fishing_technique", "new_fish_species", "water_current_pattern"],
            "M": ["mineral_deposit", "stone_quality_assessment", "ore_identification"],
            "W": ["wood_property", "tree_species_use", "cutting_technique"],
            "A": ["crop_rotation", "soil_preparation", "seed_selection"],
            "C": ["building_technique", "material_property", "structural_design"],
            "T": ["tool_design", "material_combination", "crafting_technique"],
            "R": ["natural_phenomenon", "star_pattern", "weather_prediction"],
            "E": ["terrain_feature", "navigation_landmark", "resource_location"]
        }
        
        if category in discoveries:
            discovery_type = random.choice(discoveries[category])
            return {
                "type": discovery_type,
                "description": f"Discovered new knowledge about {discovery_type}",
                "value": random.randint(1, 5)
            }
        
        return None
    
    def _process_observations(self, action_code, terrain_code):
        """Process observations from actions that could lead to discoveries."""
        # Check which observation triggers this action might contribute to
        for observation_name, trigger_data in self.progression_paths["observation_triggers"].items():
            required_actions = set(trigger_data.get("required_actions", []))
            
            # If this action contributes to the observation
            if action_code in required_actions:
                # Initialize observation counter if needed
                if observation_name not in self.observations:
                    self.observations[observation_name] = 0
                
                # Increment observation counter
                self.observations[observation_name] += 1
                
                # Check terrain factors if applicable
                terrain_factors = trigger_data.get("terrain_factors", [])
                if terrain_factors and self.terrain_system:
                    for factor in terrain_factors:
                        if factor == "special_features" and len(terrain_code) > 4 and terrain_code[4]:
                            # Special feature present, bonus observation
                            self.observations[observation_name] += 1
                        elif factor in ["elevation", "moisture", "temperature", "fertility"]:
                            # Higher values in these factors give bonus observations
                            factor_index = {"elevation": 0, "moisture": 1, "temperature": 2, "fertility": 3}
                            if factor in factor_index:
                                factor_value = int(terrain_code[factor_index[factor]])
                                if factor_value >= 7:  # High value
                                    self.observations[observation_name] += 1
    
    def _check_technology_unlocks(self):
        """Check if any new technologies can be unlocked."""
        for tech_name, tech_data in self.progression_paths["technology_prerequisites"].items():
            # Skip if already unlocked
            if tech_name in self.available_technologies:
                continue
                
            # Check required actions
            required_actions = set(tech_data.get("required_actions", []))
            if not required_actions.issubset(self.completed_actions):
                continue
                
            # Check required observations
            required_observations = tech_data.get("required_observations", [])
            observations_met = True
            for obs in required_observations:
                if obs not in self.observations or self.observations[obs] < self.progression_paths["observation_triggers"][obs]["minimum_observations"]:
                    observations_met = False
                    break
                    
            if not observations_met:
                continue
                
            # Check required tools
            required_tools = set(tech_data.get("required_tools", []))
            if not required_tools.issubset(self.available_tools):
                continue
                
            # Check required resources
            required_resources = tech_data.get("required_resources", [])
            resources_met = True
            for resource in required_resources:
                if resource not in self.resources or self.resources[resource] < 5:  # Arbitrary threshold
                    resources_met = False
                    break
                    
            if not resources_met:
                continue
                
            # All requirements met, unlock the technology
            self.available_technologies.add(tech_name)
            
            # Check for newly available actions
            newly_unlocked = tech_data.get("unlock_actions", [])
            
            return {
                "technology_unlocked": tech_name,
                "new_actions_available": newly_unlocked
            }
            
        return None
    
    def _check_tool_unlocks(self):
        """Check if any new tools can be created."""
        for tool_name, tool_data in self.progression_paths["tool_prerequisites"].items():
            # Skip if already available
            if tool_name in self.available_tools:
                continue
                
            # Check required actions
            required_actions = set(tool_data.get("required_actions", []))
            if not required_actions.issubset(self.completed_actions):
                continue
                
            # Check required resources
            required_resources = tool_data.get("required_resources", [])
            resources_met = True
            for resource in required_resources:
                if resource not in self.resources or self.resources[resource] < 3:  # Arbitrary threshold
                    resources_met = False
                    break
                    
            if not resources_met:
                continue
                
            # Check required knowledge
            required_knowledge = set(tool_data.get("required_knowledge", []))
            if not required_knowledge.issubset(self.available_technologies):
                continue
                
            # All requirements met, unlock the tool
            self.available_tools.add(tool_name)
            
            # Check for newly available actions
            newly_unlocked = tool_data.get("unlock_actions", [])
            
            return {
                "tool_unlocked": tool_name,
                "new_actions_available": newly_unlocked
            }
            
        return None
    
    def _check_era_advancement(self):
        """Check if the colony can advance to the next era."""
        current_era_data = self.progression_paths["era_progression"].get(self.current_era, {})
        advancement_requirements = current_era_data.get("advancement_requirements", {})
        
        # No advancement requirements defined
        if not advancement_requirements:
            return None
            
        # Check required technologies
        required_technologies = set(advancement_requirements.get("technologies", []))
        if not required_technologies.issubset(self.available_technologies):
            return None
            
        # Check required tools
        required_tools = set(advancement_requirements.get("tools", []))
        if not required_tools.issubset(self.available_tools):
            return None
            
        # Check required resources
        required_resources = advancement_requirements.get("resources", [])
        for resource in required_resources:
            if resource not in self.resources or self.resources[resource] < 10:  # Arbitrary threshold
                return None
                
        # Check required structures (simplified)
        required_structures = advancement_requirements.get("structures", [])
        if required_structures:
            # This would need to be implemented with a proper structure tracking system
            return None
            
        # Check required social organization (simplified)
        required_social = advancement_requirements.get("social_organization", [])
        if required_social:
            # This would need to be implemented with a proper social system
            return None
            
        # All requirements met, advance to next era
        next_era = self._get_next_era()
        if next_era:
            self.current_era = next_era
            
            # Get starting actions for the new era
            new_era_data = self.progression_paths["era_progression"].get(next_era, {})
            new_actions = new_era_data.get("starting_actions", [])
            
            return {
                "era_advanced": next_era,
                "new_actions_available": new_actions
            }
            
        return None
    
    def _get_next_era(self):
        """Determine the next era based on the current era."""
        era_sequence = ["stone_age", "bronze_age", "iron_age", "medieval", 
                        "renaissance", "industrial", "modern", "information_age", "space_age"]
        
        try:
            current_index = era_sequence.index(self.current_era)
            if current_index < len(era_sequence) - 1:
                return era_sequence[current_index + 1]
        except ValueError:
            pass
            
        return None
    
    def get_action_details(self, action_code):
        """
        Get detailed information about a specific action.
        
        Args:
            action_code: Code of the action
            
        Returns:
            Dictionary with action details
        """
        action_data = self._get_action_data(action_code)
        if not action_data:
            return {"error": f"Unknown action: {action_code}"}
            
        return action_data
    
    def set_current_era(self, era):
        """
        Set the current technological era.
        
        Args:
            era: Era name (stone_age, bronze_age, etc.)
        """
        valid_eras = [
            "stone_age", "bronze_age", "iron_age", "medieval", 
            "renaissance", "industrial", "modern", "information_age", "space_age"
        ]
        
        if era not in valid_eras:
            raise ValueError(f"Invalid era: {era}. Must be one of {valid_eras}")
            
        self.current_era = era
    
    def add_resource(self, resource_name, amount):
        """
        Add resources to the colony's inventory.
        
        Args:
            resource_name: Name of the resource
            amount: Amount to add
        """
        if resource_name in self.resources:
            self.resources[resource_name] += amount
        else:
            self.resources[resource_name] = amount
    
    def add_tool(self, tool_name):
        """
        Add a tool to the colony's available tools.
        
        Args:
            tool_name: Name of the tool
        """
        self.available_tools.add(tool_name)
    
    def add_technology(self, technology_name):
        """
        Add a technology to the colony's knowledge.
        
        Args:
            technology_name: Name of the technology
        """
        self.available_technologies.add(technology_name)
    
    def get_recommended_actions(self, terrain_code, group_size=1, focus_area=None):
        """
        Get recommended actions based on colony needs and terrain.
        
        Args:
            terrain_code: 5-digit terrain code
            group_size: Number of colonists available
            focus_area: Optional focus area (food, shelter, tools, etc.)
            
        Returns:
            List of recommended action codes with reasons
        """
        available_actions = self.get_available_actions(terrain_code, group_size)
        
        # No available actions
        if not available_actions:
            return []
            
        recommendations = []
        
        # Prioritize actions based on colony needs and focus area
        for action_code in available_actions:
            action_data = self._get_action_data(action_code)
            if not action_data:
                continue
                
            priority = 0
            reason = ""
            
            # Check outcomes for relevant resources
            outcomes = action_data.get("outcomes", {})
            
            # Food priority
            if "food" in outcomes or "future_food" in outcomes:
                if focus_area == "food" or "food" not in self.resources or self.resources.get("food", 0) < 10:
                    priority += 3
                    reason = "Food is a critical need"
                    
            # Shelter priority
            if "shelter" in outcomes:
                if focus_area == "shelter" or "shelter" not in self.resources or self.resources.get("shelter", 0) < 5:
                    priority += 2
                    reason = "Shelter is needed"
                    
            # Tool materials priority
            if any(r in outcomes for r in ["wood", "stone", "bone"]):
                if focus_area == "tools" or len(self.available_tools) < 3:
                    priority += 2
                    reason = "Materials for tools are needed"
                    
            # Knowledge priority
            if "knowledge" in outcomes or "discovery_chance" in outcomes:
                if focus_area == "knowledge" or len(self.available_technologies) < 2:
                    priority += 1
                    reason = "Knowledge acquisition is important"
                    
            # Add to recommendations if it has any priority
            if priority > 0:
                recommendations.append({
                    "action_code": action_code,
                    "name": action_data["name"],
                    "priority": priority,
                    "reason": reason
                })
        
        # Sort by priority (highest first)
        recommendations.sort(key=lambda x: x["priority"], reverse=True)
        
        return recommendations
