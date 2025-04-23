"""
Resource System for Autonomous Realms

This module handles resource management, crafting, and technological progression
for the colony simulation.
"""

import random
import json
import os
import math
from pathlib import Path

class ResourceSystem:
    """
    Manages resources, crafting, and technological progression for colony simulation.
    Tracks available resources, enables crafting based on available materials and knowledge,
    and guides technological progression through realistic pathways.
    """
    
    def __init__(self, data_path="data/resources", terrain_system=None, action_system=None):
        """
        Initialize the resource system with configuration data.
        
        Args:
            data_path: Path to resource data files
            terrain_system: Reference to the terrain system
            action_system: Reference to the action system
        """
        self.data_path = data_path
        self.terrain_system = terrain_system
        self.action_system = action_system
        
        # Load resource data
        self.resource_codes = self._load_json("resource_codes.json")
        self.crafting_recipes = self._load_json("crafting_recipes.json")
        self.technology_progression = self._load_json("technology_progression.json")
        
        # Initialize resource tracking
        self.resources = {}
        self.tools = set()
        self.facilities = set()
        self.technologies = set()
        self.observations = {}
        
        # Current era
        self.current_era = "stone_age"
        
        # Colonist skill tracking (simplified)
        self.colonist_skills = {}
        
    def _load_json(self, filename):
        """Load JSON data from file."""
        file_path = os.path.join(self.data_path, filename)
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def add_resource(self, resource_code, amount):
        """
        Add resources to the colony's inventory.
        
        Args:
            resource_code: Code of the resource (e.g., "B-001")
            amount: Amount to add
            
        Returns:
            Dictionary with operation result
        """
        # Validate resource code
        if not self._is_valid_resource(resource_code):
            return {"success": False, "message": f"Invalid resource code: {resource_code}"}
        
        # Add resource to inventory
        if resource_code in self.resources:
            self.resources[resource_code] += amount
        else:
            self.resources[resource_code] = amount
            
        # Get resource name for the message
        resource_name = self._get_resource_name(resource_code)
        
        return {
            "success": True, 
            "message": f"Added {amount} {resource_name} to inventory",
            "current_amount": self.resources[resource_code]
        }
    
    def remove_resource(self, resource_code, amount):
        """
        Remove resources from the colony's inventory.
        
        Args:
            resource_code: Code of the resource (e.g., "B-001")
            amount: Amount to remove
            
        Returns:
            Dictionary with operation result
        """
        # Validate resource code
        if not self._is_valid_resource(resource_code):
            return {"success": False, "message": f"Invalid resource code: {resource_code}"}
        
        # Check if we have enough
        if resource_code not in self.resources or self.resources[resource_code] < amount:
            return {"success": False, "message": f"Not enough {self._get_resource_name(resource_code)} available"}
        
        # Remove resource from inventory
        self.resources[resource_code] -= amount
        
        # Remove entry if amount is zero
        if self.resources[resource_code] <= 0:
            del self.resources[resource_code]
            
        # Get resource name for the message
        resource_name = self._get_resource_name(resource_code)
        
        return {
            "success": True, 
            "message": f"Removed {amount} {resource_name} from inventory",
            "current_amount": self.resources.get(resource_code, 0)
        }
    
    def _is_valid_resource(self, resource_code):
        """Check if a resource code is valid."""
        return (resource_code in self.resource_codes["resource_codes"] or 
                resource_code in self.crafting_recipes["recipes"])
    
    def _get_resource_name(self, resource_code):
        """Get the name of a resource from its code."""
        if resource_code in self.resource_codes["resource_codes"]:
            return self.resource_codes["resource_codes"][resource_code]["name"]
        elif resource_code in self.crafting_recipes["recipes"]:
            return resource_code  # For tools and facilities not in resource_codes
        return resource_code  # Fallback
    
    def get_resource_details(self, resource_code):
        """
        Get detailed information about a specific resource.
        
        Args:
            resource_code: Code of the resource
            
        Returns:
            Dictionary with resource details
        """
        if resource_code in self.resource_codes["resource_codes"]:
            details = self.resource_codes["resource_codes"][resource_code].copy()
            details["available"] = self.resources.get(resource_code, 0)
            
            # Add era availability info
            details["available_in_current_era"] = (
                details.get("first_available", "stone_age") <= self.current_era
            )
            
            # Add tool requirements if any
            if resource_code in self.resource_codes["resource_dependencies"]["tool_requirements"]:
                details["required_tools"] = self.resource_codes["resource_dependencies"]["tool_requirements"][resource_code]
                
            # Add knowledge requirements if any
            if resource_code in self.resource_codes["resource_dependencies"]["knowledge_requirements"]:
                details["required_knowledge"] = self.resource_codes["resource_dependencies"]["knowledge_requirements"][resource_code]
                
            return details
        elif resource_code in self.crafting_recipes["recipes"]:
            # For tools and facilities
            details = self.crafting_recipes["recipes"][resource_code].copy()
            details["available"] = 1 if resource_code in self.tools or resource_code in self.facilities else 0
            return details
            
        return {"error": f"Unknown resource: {resource_code}"}
    
    def get_available_resources(self):
        """
        Get a list of all available resources and their amounts.
        
        Returns:
            Dictionary of resources and their amounts
        """
        result = {}
        
        # Add inventory resources
        for resource_code, amount in self.resources.items():
            result[resource_code] = {
                "name": self._get_resource_name(resource_code),
                "amount": amount
            }
            
        # Add tools
        for tool in self.tools:
            result[tool] = {
                "name": tool,
                "amount": 1,
                "type": "tool"
            }
            
        # Add facilities
        for facility in self.facilities:
            result[facility] = {
                "name": facility,
                "amount": 1,
                "type": "facility"
            }
            
        return result
    
    def get_craftable_items(self):
        """
        Get a list of items that can be crafted with current resources and knowledge.
        
        Returns:
            List of craftable items with their requirements
        """
        craftable_items = []
        
        for item_code, recipe in self.crafting_recipes["recipes"].items():
            # Skip if not in current era
            if recipe["era"] > self.current_era:
                continue
                
            # Check if we have required tools
            tools_required = set(recipe.get("tools_required", []))
            if not tools_required.issubset(self.tools):
                continue
                
            # Check if we have required knowledge
            knowledge_required = set(recipe.get("knowledge_required", []))
            if not knowledge_required.issubset(self.technologies):
                continue
                
            # Check if we have required facility
            facility_required = recipe.get("facility_required", "")
            if facility_required and facility_required not in self.facilities:
                continue
                
            # Check if we have required resources
            has_resources = True
            required_resources = []
            
            for input_item in recipe["inputs"]:
                resource = input_item["resource"]
                amount = input_item["amount"]
                optional = input_item.get("optional", False)
                alternatives = input_item.get("alternatives", [])
                
                # Check main resource
                if resource in self.resources and self.resources[resource] >= amount:
                    required_resources.append({
                        "resource": resource,
                        "name": self._get_resource_name(resource),
                        "amount": amount,
                        "available": self.resources[resource]
                    })
                    continue
                    
                # Check alternatives
                alt_found = False
                for alt in alternatives:
                    if alt in self.resources and self.resources[alt] >= amount:
                        required_resources.append({
                            "resource": alt,
                            "name": self._get_resource_name(alt),
                            "amount": amount,
                            "available": self.resources[alt]
                        })
                        alt_found = True
                        break
                        
                # If optional, continue
                if optional:
                    continue
                    
                # If we found an alternative, continue
                if alt_found:
                    continue
                    
                # If we get here, we don't have the required resources
                has_resources = False
                break
                
            if has_resources:
                craftable_items.append({
                    "item_code": item_code,
                    "name": recipe.get("output", {}).get("resource", item_code),
                    "category": recipe["category"],
                    "required_resources": required_resources,
                    "labor_time": recipe["labor_time"],
                    "skill_difficulty": recipe["skill_difficulty"]
                })
                
        return craftable_items
    
    def craft_item(self, item_code, colonist_ids=None):
        """
        Attempt to craft an item using available resources.
        
        Args:
            item_code: Code of the item to craft
            colonist_ids: List of colonist IDs performing the crafting
            
        Returns:
            Dictionary with crafting result
        """
        # Check if recipe exists
        if item_code not in self.crafting_recipes["recipes"]:
            return {"success": False, "message": f"Unknown crafting recipe: {item_code}"}
            
        recipe = self.crafting_recipes["recipes"][item_code]
        
        # Check if in current era
        if recipe["era"] > self.current_era:
            return {"success": False, "message": f"This recipe is not available in the current era"}
            
        # Check if we have required tools
        tools_required = set(recipe.get("tools_required", []))
        if not tools_required.issubset(self.tools):
            missing_tools = tools_required - self.tools
            return {"success": False, "message": f"Missing required tools: {', '.join(missing_tools)}"}
            
        # Check if we have required knowledge
        knowledge_required = set(recipe.get("knowledge_required", []))
        if not knowledge_required.issubset(self.technologies):
            missing_knowledge = knowledge_required - self.technologies
            return {"success": False, "message": f"Missing required knowledge: {', '.join(missing_knowledge)}"}
            
        # Check if we have required facility
        facility_required = recipe.get("facility_required", "")
        if facility_required and facility_required not in self.facilities:
            return {"success": False, "message": f"Missing required facility: {facility_required}"}
            
        # Check and consume required resources
        resources_to_consume = []
        
        for input_item in recipe["inputs"]:
            resource = input_item["resource"]
            amount = input_item["amount"]
            optional = input_item.get("optional", False)
            alternatives = input_item.get("alternatives", [])
            
            # Check main resource
            if resource in self.resources and self.resources[resource] >= amount:
                resources_to_consume.append({"resource": resource, "amount": amount})
                continue
                
            # Check alternatives
            alt_found = False
            for alt in alternatives:
                if alt in self.resources and self.resources[alt] >= amount:
                    resources_to_consume.append({"resource": alt, "amount": amount})
                    alt_found = True
                    break
                    
            # If optional, continue
            if optional:
                continue
                
            # If we found an alternative, continue
            if alt_found:
                continue
                
            # If we get here, we don't have the required resources
            return {"success": False, "message": f"Not enough {self._get_resource_name(resource)} available"}
            
        # Calculate success chance
        success_chance = self._calculate_crafting_success_chance(recipe, colonist_ids)
        
        # Determine if crafting succeeds
        success = random.random() < success_chance
        
        # Consume resources regardless of success
        for resource_info in resources_to_consume:
            self.remove_resource(resource_info["resource"], resource_info["amount"])
            
        # Process result
        result = {
            "success": success,
            "message": f"{'Successfully crafted' if success else 'Failed to craft'} {item_code}",
            "resources_consumed": resources_to_consume
        }
        
        if success:
            # Add crafted item
            output = recipe.get("output", {})
            output_resource = output.get("resource", item_code)
            output_amount = output.get("amount", 1)
            
            # Check if it's a tool or facility
            if recipe["category"] in ["tools", "weapons"]:
                self.tools.add(output_resource)
                result["message"] = f"Successfully crafted {output_resource}"
            elif recipe["category"] in ["construction", "metallurgy"] and "facility" in output_resource:
                self.facilities.add(output_resource)
                result["message"] = f"Successfully built {output_resource}"
            else:
                # Regular resource
                self.add_resource(output_resource, output_amount)
                result["message"] = f"Successfully crafted {output_amount} {self._get_resource_name(output_resource)}"
                
            # Process byproducts
            byproducts = []
            for byproduct in recipe.get("byproducts", []):
                if random.random() < byproduct.get("chance", 1.0):
                    byproduct_resource = byproduct["resource"]
                    byproduct_amount = byproduct["amount"]
                    self.add_resource(byproduct_resource, byproduct_amount)
                    byproducts.append({
                        "resource": byproduct_resource,
                        "name": self._get_resource_name(byproduct_resource),
                        "amount": byproduct_amount
                    })
                    
            if byproducts:
                result["byproducts"] = byproducts
                
            # Update colonist skills
            if colonist_ids:
                self._update_colonist_skills(colonist_ids, recipe["category"], recipe["skill_difficulty"], success)
                
            # Check for technology discoveries
            tech_discovery = self._check_technology_discovery(recipe["category"])
            if tech_discovery:
                result["technology_discovery"] = tech_discovery
        else:
            # Failed crafting
            # Calculate resource loss
            difficulty_level = self.crafting_recipes["skill_difficulty_levels"][recipe["skill_difficulty"]]
            resource_loss_rate = difficulty_level["failure_resource_loss"]
            
            # Check for critical failure
            critical_failure = random.random() < difficulty_level["critical_failure_chance"]
            if critical_failure:
                result["critical_failure"] = True
                
                # Determine critical failure effects
                critical_effects = []
                
                # Tool damage
                if random.random() < self.crafting_recipes["critical_outcomes"]["failure"]["tool_damage"]["chance"]:
                    damage_rate = random.uniform(
                        self.crafting_recipes["critical_outcomes"]["failure"]["tool_damage"]["min"],
                        self.crafting_recipes["critical_outcomes"]["failure"]["tool_damage"]["max"]
                    )
                    
                    # Simplified: just mention tool damage
                    critical_effects.append("Tool damage occurred")
                    
                # Injury chance
                injury_chance = random.uniform(
                    self.crafting_recipes["critical_outcomes"]["failure"]["injury_chance"]["min"],
                    self.crafting_recipes["critical_outcomes"]["failure"]["injury_chance"]["max"]
                )
                
                if random.random() < injury_chance:
                    critical_effects.append("Injury occurred during crafting")
                    
                result["critical_effects"] = critical_effects
                
        return result
    
    def _calculate_crafting_success_chance(self, recipe, colonist_ids=None):
        """Calculate the chance of successful crafting based on recipe difficulty and colonist skills."""
        # Get base success rate from difficulty
        difficulty_level = self.crafting_recipes["skill_difficulty_levels"][recipe["skill_difficulty"]]
        base_success_rate = difficulty_level["base_success_rate"]
        
        # Calculate skill bonus (simplified)
        skill_bonus = 0
        if colonist_ids:
            # Average skill level of participating colonists
            category = recipe["category"]
            total_skill = 0
            for colonist_id in colonist_ids:
                if colonist_id in self.colonist_skills and category in self.colonist_skills[colonist_id]:
                    total_skill += self.colonist_skills[colonist_id][category]
                    
            if len(colonist_ids) > 0:
                avg_skill = total_skill / len(colonist_ids)
                skill_bonus = avg_skill * difficulty_level["skill_impact"]
                
        # Group size bonus (simplified)
        group_size_bonus = 0
        if colonist_ids and len(colonist_ids) > 1:
            # More people generally helps, up to a point
            optimal_size = 3  # Simplified assumption
            size_factor = min(len(colonist_ids) / optimal_size, 2)  # Cap at 2x bonus
            group_size_bonus = 0.05 * (size_factor - 1)  # Up to 5% bonus
            
        # Final success chance
        success_chance = base_success_rate + skill_bonus + group_size_bonus
        
        # Ensure within bounds
        return max(0.1, min(0.95, success_chance))
    
    def _update_colonist_skills(self, colonist_ids, category, difficulty, success):
        """Update colonist skills based on crafting experience."""
        # Skill gain factors based on difficulty
        difficulty_factors = {
            "very_low": 0.01,
            "low": 0.02,
            "medium": 0.03,
            "high": 0.04,
            "very_high": 0.05
        }
        
        # Base skill gain
        base_gain = difficulty_factors.get(difficulty, 0.02)
        
        # Adjust based on success/failure
        skill_gain = base_gain * (1.5 if success else 0.5)
        
        # Update each colonist's skill
        for colonist_id in colonist_ids:
            if colonist_id not in self.colonist_skills:
                self.colonist_skills[colonist_id] = {}
                
            if category not in self.colonist_skills[colonist_id]:
                self.colonist_skills[colonist_id][category] = 0
                
            # Add skill, with diminishing returns as skill increases
            current_skill = self.colonist_skills[colonist_id][category]
            diminishing_factor = max(0.1, 1.0 - (current_skill / 10.0))  # Skill gain slows as skill increases
            
            self.colonist_skills[colonist_id][category] += skill_gain * diminishing_factor
            
            # Cap skill at 10
            self.colonist_skills[colonist_id][category] = min(10, self.colonist_skills[colonist_id][category])
    
    def add_observation(self, observation_type, amount=1, terrain_code=None):
        """
        Add observations that can lead to technology discoveries.
        
        Args:
            observation_type: Type of observation
            amount: Number of observations to add
            terrain_code: Optional terrain code where observation occurred
            
        Returns:
            Dictionary with operation result
        """
        # Validate observation type
        if observation_type not in self.technology_progression["observation_types"]:
            return {"success": False, "message": f"Invalid observation type: {observation_type}"}
            
        # Initialize observation counter if needed
        if observation_type not in self.observations:
            self.observations[observation_type] = 0
            
        # Add observations
        self.observations[observation_type] += amount
        
        # Apply terrain factors if applicable
        if terrain_code and self.terrain_system:
            terrain_factors = self.technology_progression["observation_types"][observation_type].get("terrain_factors", [])
            
            for factor in terrain_factors:
                if factor == "special_features" and len(terrain_code) > 4 and terrain_code[4]:
                    # Special feature present, bonus observation
                    self.observations[observation_type] += 1
                elif factor in ["elevation", "moisture", "temperature", "fertility"]:
                    # Higher values in these factors give bonus observations
                    factor_index = {"elevation": 0, "moisture": 1, "temperature": 2, "fertility": 3}
                    if factor in factor_index:
                        factor_value = int(terrain_code[factor_index[factor]])
                        if factor_value >= 7:  # High value
                            self.observations[observation_type] += 1
        
        # Check if this leads to any technology discoveries
        tech_discovery = self._check_technology_discovery_from_observation(observation_type)
        
        result = {
            "success": True,
            "message": f"Added {amount} observations to {observation_type}",
            "current_observations": self.observations[observation_type],
            "minimum_required": self.technology_progression["observation_types"][observation_type]["minimum_observations"]
        }
        
        if tech_discovery:
            result["technology_discovery"] = tech_discovery
            
        return result
    
    def _check_technology_discovery_from_observation(self, observation_type):
        """Check if an observation leads to technology discovery."""
        # Get minimum observations required
        min_observations = self.technology_progression["observation_types"][observation_type]["minimum_observations"]
        
        # Check if we have enough observations
        if self.observations.get(observation_type, 0) < min_observations:
            return None
            
        # Check which technologies require this observation
        for era, technologies in self.technology_progression["technology_tree"].items():
            # Skip future eras
            if self._get_era_index(era) > self._get_era_index(self.current_era):
                continue
                
            for tech_name, tech_data in technologies.items():
                # Skip if already discovered
                if tech_name in self.technologies:
                    continue
                    
                # Check if this observation is required
                if observation_type in tech_data.get("required_observations", []):
                    # Check if all required observations are met
                    all_observations_met = True
                    for req_obs in tech_data.get("required_observations", []):
                        req_min = self.technology_progression["observation_types"][req_obs]["minimum_observations"]
                        if self.observations.get(req_obs, 0) < req_min:
                            all_observations_met = False
                            break
                            
                    if not all_observations_met:
                        continue
                        
                    # Check prerequisites
                    prerequisites_met = True
                    for prereq in tech_data.get("prerequisites", []):
                        if prereq not in self.technologies:
                            prerequisites_met = False
                            break
                            
                    if not prerequisites_met:
                        continue
                        
                    # Check resources
                    resources_met = True
                    for resource in tech_data.get("required_resources", []):
                        if resource not in self.resources or self.resources[resource] < 1:
                            resources_met = False
                            break
                            
                    if not resources_met:
                        continue
                        
                    # Calculate discovery chance
                    discovery_chance = self._calculate_technology_discovery_chance(tech_data)
                    
                    # Check if discovery occurs
                    if random.random() < discovery_chance:
                        # Add technology
                        self.technologies.add(tech_name)
                        
                        # Return discovery info
                        return {
                            "technology": tech_name,
                            "description": tech_data["description"],
                            "unlocks": tech_data.get("unlocks", [])
                        }
        
        return None
    
    def _check_technology_discovery(self, activity_category=None):
        """Check for technology discoveries based on colony activities."""
        # Map crafting categories to relevant observation types
        category_to_observation = {
            "tools": ["stone_properties", "metal_properties"],
            "weapons": ["combat_techniques", "metal_properties"],
            "containers": ["clay_properties", "fiber_properties"],
            "clothing": ["hide_properties", "fiber_properties"],
            "construction": ["structural_principles", "stone_properties"],
            "food_processing": ["food_spoilage"],
            "metallurgy": ["ore_properties", "fire_effects", "metal_properties"],
            "medicine": ["plant_properties", "disease_patterns"]
        }
        
        # If no specific category, check all technologies
        if not activity_category:
            # Check each technology in current era
            for tech_name, tech_data in self.technology_progression["technology_tree"].get(self.current_era, {}).items():
                # Skip if already discovered
                if tech_name in self.technologies:
                    continue
                    
                # Check prerequisites
                prerequisites_met = True
                for prereq in tech_data.get("prerequisites", []):
                    if prereq not in self.technologies:
                        prerequisites_met = False
                        break
                        
                if not prerequisites_met:
                    continue
                    
                # Check observations
                observations_met = True
                for obs in tech_data.get("required_observations", []):
                    min_obs = self.technology_progression["observation_types"][obs]["minimum_observations"]
                    if self.observations.get(obs, 0) < min_obs:
                        observations_met = False
                        break
                        
                if not observations_met:
                    continue
                    
                # Check resources
                resources_met = True
                for resource in tech_data.get("required_resources", []):
                    if resource not in self.resources or self.resources[resource] < 1:
                        resources_met = False
                        break
                        
                if not resources_met:
                    continue
                    
                # Calculate discovery chance
                discovery_chance = self._calculate_technology_discovery_chance(tech_data)
                
                # Check if discovery occurs
                if random.random() < discovery_chance:
                    # Add technology
                    self.technologies.add(tech_name)
                    
                    # Return discovery info
                    return {
                        "technology": tech_name,
                        "description": tech_data["description"],
                        "unlocks": tech_data.get("unlocks", [])
                    }
        else:
            # Check technologies related to the specific category
            relevant_observations = category_to_observation.get(activity_category, [])
            
            # Small chance of random observation in this field
            for obs in relevant_observations:
                if random.random() < 0.1:  # 10% chance
                    self.add_observation(obs, 1)
                    
            # Then check for discoveries as normal
            return self._check_technology_discovery_from_observation(random.choice(relevant_observations)) if relevant_observations else None
            
        return None
    
    def _calculate_technology_discovery_chance(self, tech_data):
        """Calculate the chance of discovering a technology."""
        # Get base discovery chance from difficulty
        difficulty = tech_data.get("discovery_difficulty", "medium")
        difficulty_data = self.technology_progression["discovery_difficulty_levels"][difficulty]
        
        base_chance = difficulty_data["base_discovery_chance"]
        
        # Calculate observation bonus
        observation_bonus = 0
        for obs in tech_data.get("required_observations", []):
            min_obs = self.technology_progression["observation_types"][obs]["minimum_observations"]
            actual_obs = self.observations.get(obs, 0)
            
            # Bonus for observations beyond minimum
            if actual_obs > min_obs:
                excess = actual_obs - min_obs
                observation_bonus += excess * difficulty_data["observation_multiplier"]
                
        # Knowledge bonus from related technologies
        knowledge_bonus = 0
        for prereq in tech_data.get("prerequisites", []):
            if prereq in self.technologies:
                knowledge_bonus += difficulty_data["knowledge_bonus"]
                
        # Final discovery chance
        discovery_chance = base_chance + observation_bonus + knowledge_bonus
        
        # Ensure within bounds
        return max(0.01, min(0.5, discovery_chance))
    
    def get_available_technologies(self):
        """
        Get a list of all discovered technologies.
        
        Returns:
            Dictionary of technologies and their details
        """
        result = {}
        
        for tech_name in self.technologies:
            # Find technology data
            tech_data = None
            tech_era = None
            
            for era, technologies in self.technology_progression["technology_tree"].items():
                if tech_name in technologies:
                    tech_data = technologies[tech_name]
                    tech_era = era
                    break
                    
            if tech_data:
                result[tech_name] = {
                    "name": tech_name,
                    "description": tech_data["description"],
                    "era": tech_era,
                    "unlocks": tech_data.get("unlocks", []),
                    "knowledge_type": tech_data.get("knowledge_type", "technical")
                }
                
        return result
    
    def get_discoverable_technologies(self):
        """
        Get a list of technologies that could potentially be discovered soon.
        
        Returns:
            List of discoverable technologies with their requirements
        """
        discoverable = []
        
        # Check each technology in current era
        for tech_name, tech_data in self.technology_progression["technology_tree"].get(self.current_era, {}).items():
            # Skip if already discovered
            if tech_name in self.technologies:
                continue
                
            # Check prerequisites
            missing_prerequisites = []
            for prereq in tech_data.get("prerequisites", []):
                if prereq not in self.technologies:
                    missing_prerequisites.append(prereq)
                    
            # Check observations
            missing_observations = []
            observation_progress = []
            for obs in tech_data.get("required_observations", []):
                min_obs = self.technology_progression["observation_types"][obs]["minimum_observations"]
                current_obs = self.observations.get(obs, 0)
                
                if current_obs < min_obs:
                    missing_observations.append(obs)
                    observation_progress.append({
                        "name": obs,
                        "current": current_obs,
                        "required": min_obs,
                        "progress": current_obs / min_obs
                    })
                else:
                    observation_progress.append({
                        "name": obs,
                        "current": current_obs,
                        "required": min_obs,
                        "progress": 1.0
                    })
                    
            # Check resources
            missing_resources = []
            for resource in tech_data.get("required_resources", []):
                if resource not in self.resources or self.resources[resource] < 1:
                    missing_resources.append(resource)
                    
            # Calculate overall progress
            prereq_progress = 1.0 if not tech_data.get("prerequisites", []) else (
                (len(tech_data.get("prerequisites", [])) - len(missing_prerequisites)) / 
                max(1, len(tech_data.get("prerequisites", [])))
            )
            
            obs_progress = 1.0
            if observation_progress:
                obs_progress = sum(p["progress"] for p in observation_progress) / len(observation_progress)
                
            resource_progress = 1.0 if not tech_data.get("required_resources", []) else (
                (len(tech_data.get("required_resources", [])) - len(missing_resources)) / 
                max(1, len(tech_data.get("required_resources", [])))
            )
            
            overall_progress = (prereq_progress + obs_progress + resource_progress) / 3
            
            # Add to discoverable list if making progress
            if overall_progress > 0:
                discoverable.append({
                    "name": tech_name,
                    "description": tech_data["description"],
                    "missing_prerequisites": missing_prerequisites,
                    "observation_progress": observation_progress,
                    "missing_resources": missing_resources,
                    "overall_progress": overall_progress,
                    "discovery_difficulty": tech_data["discovery_difficulty"]
                })
                
        # Sort by progress (highest first)
        discoverable.sort(key=lambda x: x["overall_progress"], reverse=True)
        
        return discoverable
    
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
        
        # Sync with other systems if available
        if self.terrain_system:
            self.terrain_system.set_current_era(era)
            
        if self.action_system:
            self.action_system.set_current_era(era)
    
    def _get_era_index(self, era):
        """Get the index of an era in the progression sequence."""
        era_sequence = [
            "stone_age", "bronze_age", "iron_age", "medieval", 
            "renaissance", "industrial", "modern", "information_age", "space_age"
        ]
        
        try:
            return era_sequence.index(era)
        except ValueError:
            return -1
    
    def check_era_advancement(self):
        """
        Check if the colony can advance to the next era.
        
        Returns:
            Dictionary with advancement result or None if not ready
        """
        current_index = self._get_era_index(self.current_era)
        if current_index == -1 or current_index >= 8:  # No advancement beyond space_age
            return None
            
        next_era = ["stone_age", "bronze_age", "iron_age", "medieval", 
                   "renaissance", "industrial", "modern", "information_age", "space_age"][current_index + 1]
        
        # Define requirements for each era transition
        era_requirements = {
            "stone_age_to_bronze_age": {
                "technologies": ["basic_metallurgy", "bronze_working"],
                "resources": ["M-004", "M-005", "M-006"],
                "tools": ["furnace"]
            },
            "bronze_age_to_iron_age": {
                "technologies": ["iron_working", "advanced_metallurgy"],
                "resources": ["M-007"],
                "tools": ["advanced_furnace"]
            },
            "iron_age_to_medieval": {
                "technologies": ["masonry", "engineering"],
                "resources": ["M-007"],
                "tools": ["iron_tools"]
            },
            "medieval_to_renaissance": {
                "technologies": ["mathematics", "astronomy_basic"],
                "resources": [],
                "tools": []
            },
            "renaissance_to_industrial": {
                "technologies": [],  # Would define actual requirements
                "resources": [],
                "tools": []
            },
            "industrial_to_modern": {
                "technologies": [],  # Would define actual requirements
                "resources": [],
                "tools": []
            },
            "modern_to_information_age": {
                "technologies": [],  # Would define actual requirements
                "resources": [],
                "tools": []
            },
            "information_age_to_space_age": {
                "technologies": [],  # Would define actual requirements
                "resources": [],
                "tools": []
            }
        }
        
        # Get requirements for current transition
        transition_key = f"{self.current_era}_to_{next_era}"
        if transition_key not in era_requirements:
            return None
            
        requirements = era_requirements[transition_key]
        
        # Check if requirements are met
        missing_requirements = {
            "technologies": [],
            "resources": [],
            "tools": []
        }
        
        # Check technologies
        for tech in requirements["technologies"]:
            if tech not in self.technologies:
                missing_requirements["technologies"].append(tech)
                
        # Check resources
        for resource in requirements["resources"]:
            if resource not in self.resources or self.resources[resource] < 1:
                missing_requirements["resources"].append(resource)
                
        # Check tools
        for tool in requirements["tools"]:
            if tool not in self.tools:
                missing_requirements["tools"].append(tool)
                
        # If any requirements are missing, return what's missing
        if any(missing_requirements.values()):
            return {
                "can_advance": False,
                "current_era": self.current_era,
                "next_era": next_era,
                "missing_requirements": missing_requirements
            }
            
        # All requirements met, advance to next era
        self.set_current_era(next_era)
        
        return {
            "can_advance": True,
            "advanced_to": next_era,
            "message": f"Advanced to {next_era}!"
        }
    
    def process_resource_decay(self, days=1):
        """
        Process natural decay of resources over time.
        
        Args:
            days: Number of days to process
            
        Returns:
            Dictionary with decay results
        """
        decay_results = {}
        
        for resource_code, amount in list(self.resources.items()):
            # Skip if not a valid resource
            if resource_code not in self.resource_codes["resource_codes"]:
                continue
                
            resource_data = self.resource_codes["resource_codes"][resource_code]
            decay_rate_text = resource_data.get("decay_rate", "none")
            
            # Get numeric decay rate
            decay_rate = self.resource_codes["resource_properties"]["decay_rates"].get(decay_rate_text, 0.0)
            
            if decay_rate > 0:
                # Calculate decay amount
                decay_amount = amount * decay_rate * days
                
                # Apply storage modifier if applicable
                storage_req = resource_data.get("storage_requirements", "none")
                if storage_req != "none":
                    # Simplified: assume proper storage for now
                    # In a full implementation, check if proper storage exists
                    has_proper_storage = True  # Simplified
                    
                    if has_proper_storage:
                        decay_amount *= self.resource_codes["resource_properties"]["storage_modifiers"]["proper_storage"]
                    else:
                        decay_amount *= self.resource_codes["resource_properties"]["storage_modifiers"]["improper_storage"]
                        
                # Apply decay
                if decay_amount >= 1:
                    decay_amount = int(decay_amount)
                    self.resources[resource_code] -= decay_amount
                    
                    # Remove if zero or less
                    if self.resources[resource_code] <= 0:
                        del self.resources[resource_code]
                        decay_results[resource_code] = {
                            "name": resource_data["name"],
                            "amount": amount,
                            "decayed": amount,
                            "remaining": 0,
                            "fully_decayed": True
                        }
                    else:
                        decay_results[resource_code] = {
                            "name": resource_data["name"],
                            "amount": amount,
                            "decayed": decay_amount,
                            "remaining": self.resources[resource_code],
                            "fully_decayed": False
                        }
                        
        return decay_results
    
    def get_resource_categories(self):
        """
        Get a list of resource categories.
        
        Returns:
            Dictionary of resource categories
        """
        return self.resource_codes["resource_categories"]
    
    def get_resources_by_category(self, category_code):
        """
        Get resources filtered by category.
        
        Args:
            category_code: Category code (e.g., "B" for Basic Materials)
            
        Returns:
            List of resources in the category
        """
        result = []
        
        for resource_code, resource_data in self.resource_codes["resource_codes"].items():
            if resource_code.startswith(category_code):
                resource_info = resource_data.copy()
                resource_info["code"] = resource_code
                resource_info["available"] = self.resources.get(resource_code, 0)
                result.append(resource_info)
                
        return result
    
    def get_nutrition_value(self, food_resources):
        """
        Calculate the nutritional value of food resources.
        
        Args:
            food_resources: Dictionary of food resource codes and amounts
            
        Returns:
            Total nutritional value
        """
        total_nutrition = 0
        
        for resource_code, amount in food_resources.items():
            if resource_code in self.resource_codes["resource_codes"]:
                resource_data = self.resource_codes["resource_codes"][resource_code]
                
                if resource_data.get("category") == "Food Resources":
                    nutritional_value_text = resource_data.get("nutritional_value", "low")
                    nutritional_value = self.resource_codes["resource_properties"]["nutritional_values"].get(nutritional_value_text, 1)
                    
                    total_nutrition += nutritional_value * amount
                    
        return total_nutrition
    
    def get_resource_requirements(self, resource_code):
        """
        Get the requirements for obtaining a resource.
        
        Args:
            resource_code: Code of the resource
            
        Returns:
            Dictionary with resource requirements
        """
        result = {
            "tools": [],
            "knowledge": [],
            "crafting_recipe": None
        }
        
        # Check tool requirements
        if resource_code in self.resource_codes["resource_dependencies"]["tool_requirements"]:
            result["tools"] = self.resource_codes["resource_dependencies"]["tool_requirements"][resource_code]
            
        # Check knowledge requirements
        if resource_code in self.resource_codes["resource_dependencies"]["knowledge_requirements"]:
            result["knowledge"] = self.resource_codes["resource_dependencies"]["knowledge_requirements"][resource_code]
            
        # Check if it's a craftable item
        for item_code, recipe in self.crafting_recipes["recipes"].items():
            output = recipe.get("output", {})
            if output.get("resource") == resource_code:
                result["crafting_recipe"] = {
                    "recipe_code": item_code,
                    "category": recipe["category"],
                    "era": recipe["era"],
                    "inputs": recipe["inputs"],
                    "tools_required": recipe.get("tools_required", []),
                    "knowledge_required": recipe.get("knowledge_required", []),
                    "facility_required": recipe.get("facility_required", ""),
                    "labor_time": recipe["labor_time"],
                    "skill_difficulty": recipe["skill_difficulty"]
                }
                break
                
        return result
