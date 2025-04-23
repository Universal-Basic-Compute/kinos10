"""
Terrain System for Autonomous Realms

This module handles terrain generation, analysis, and effects on colony development.
It uses the terrain code system to create realistic and varied environments.
"""

import random
import json
import os
import math
from pathlib import Path

class TerrainSystem:
    """
    Manages terrain generation and analysis for colony simulation.
    Uses a 5-digit terrain code system (EMTFS) to represent different terrain types.
    """
    
    def __init__(self, data_path="data/terrain"):
        """
        Initialize the terrain system with configuration data.
        
        Args:
            data_path: Path to terrain data files
        """
        self.data_path = data_path
        self.terrain_codes = self._load_json("terrain_codes.json")
        self.terrain_resources = self._load_json("terrain_resources.json")
        self.terrain_effects = self._load_json("terrain_effects.json")
        self.current_era = "stone_age"
        
    def _load_json(self, filename):
        """Load JSON data from file."""
        file_path = os.path.join(self.data_path, filename)
        with open(file_path, 'r') as f:
            return json.load(f)
            
    def generate_terrain_map(self, width, height, seed=None):
        """
        Generate a terrain map with the specified dimensions.
        
        Args:
            width: Width of the map
            height: Height of the map
            seed: Random seed for terrain generation
            
        Returns:
            2D array of terrain codes
        """
        if seed:
            random.seed(seed)
            
        terrain_map = []
        
        # Generate base elevation using simplex noise algorithm
        elevation_map = self._generate_elevation_map(width, height)
        moisture_map = self._generate_moisture_map(width, height, elevation_map)
        temperature_map = self._generate_temperature_map(width, height, elevation_map)
        fertility_map = self._generate_fertility_map(width, height, elevation_map, moisture_map, temperature_map)
        
        # Generate terrain codes for each cell
        for y in range(height):
            row = []
            for x in range(width):
                elevation = elevation_map[y][x]
                moisture = moisture_map[y][x]
                temperature = temperature_map[y][x]
                fertility = fertility_map[y][x]
                special = self._determine_special_feature(x, y, elevation, moisture, temperature, fertility)
                
                # Create terrain code
                terrain_code = f"{elevation}{moisture}{temperature}{fertility}{special}"
                row.append(terrain_code)
            terrain_map.append(row)
            
        return terrain_map
    
    def _generate_elevation_map(self, width, height):
        """Generate elevation values for the map."""
        elevation_map = []
        for y in range(height):
            row = []
            for x in range(width):
                # Simplified noise function - in a real implementation, use Perlin or Simplex noise
                value = int(random.triangular(0, 9, 2))
                row.append(value)
            elevation_map.append(row)
        return elevation_map
    
    def _generate_moisture_map(self, width, height, elevation_map):
        """Generate moisture values based on elevation."""
        moisture_map = []
        for y in range(height):
            row = []
            for x in range(width):
                elevation = elevation_map[y][x]
                # Higher elevations tend to be drier
                base_moisture = random.triangular(0, 9, 4)
                moisture_modifier = max(0, 5 - elevation) / 5  # Higher elevation = less moisture
                value = int(base_moisture * moisture_modifier)
                row.append(min(9, max(0, value)))
            moisture_map.append(row)
        return moisture_map
    
    def _generate_temperature_map(self, width, height, elevation_map):
        """Generate temperature values based on elevation and latitude."""
        temperature_map = []
        for y in range(height):
            # Latitude effect (equator is warmer)
            latitude_factor = 1.0 - abs((y - (height / 2)) / (height / 2))
            row = []
            for x in range(width):
                elevation = elevation_map[y][x]
                # Higher elevations are cooler
                base_temp = random.triangular(0, 9, 4)
                elevation_modifier = max(0, 9 - elevation) / 9  # Higher elevation = cooler
                latitude_modifier = latitude_factor * 1.5  # Equator is warmer
                value = int(base_temp * elevation_modifier * latitude_modifier)
                row.append(min(9, max(0, value)))
            temperature_map.append(row)
        return temperature_map
    
    def _generate_fertility_map(self, width, height, elevation_map, moisture_map, temperature_map):
        """Generate fertility values based on other factors."""
        fertility_map = []
        for y in range(height):
            row = []
            for x in range(width):
                elevation = elevation_map[y][x]
                moisture = moisture_map[y][x]
                temperature = temperature_map[y][x]
                
                # Fertility is highest with moderate temperature, good moisture, and lower elevations
                elevation_factor = max(0, 5 - elevation) / 5
                moisture_factor = moisture / 9 if moisture > 2 else moisture / 18
                temp_factor = (1.0 - abs((temperature - 5) / 5))
                
                base_fertility = random.triangular(0, 9, 3)
                fertility_value = base_fertility * elevation_factor * moisture_factor * temp_factor
                value = int(fertility_value)
                row.append(min(9, max(0, value)))
            fertility_map.append(row)
        return fertility_map
    
    def _determine_special_feature(self, x, y, elevation, moisture, temperature, fertility):
        """Determine special terrain features based on terrain factors."""
        # List of possible features based on terrain characteristics
        possible_features = []
        
        # Rivers and streams in lower elevations with good moisture
        if elevation < 4 and moisture > 4:
            possible_features.append("A")  # River/Stream
            
        # Lakes in depressions with high moisture
        if elevation < 3 and moisture > 6:
            possible_features.append("B")  # Lake/Pond
            
        # Coastal areas at sea level
        if elevation == 1:
            possible_features.append("C")  # Coastal
            
        # Forests in areas with good moisture and fertility
        if 2 <= elevation <= 5 and moisture >= 4 and fertility >= 5:
            if moisture >= 6 and temperature >= 6:
                possible_features.append("J")  # Jungle/Rainforest
            elif temperature <= 2:
                possible_features.append("T")  # Taiga/Boreal forest
            elif moisture >= 6:
                possible_features.append("F")  # Dense forest
            else:
                possible_features.append("E")  # Forest
                
        # Grasslands in moderate elevations with moderate moisture
        if 1 <= elevation <= 3 and 3 <= moisture <= 5 and fertility >= 4:
            if temperature >= 6:
                possible_features.append("S")  # Savanna
            else:
                possible_features.append("G")  # Grassland
                
        # Marshes and swamps in low areas with high moisture
        if elevation <= 2 and moisture >= 7:
            possible_features.append("M")  # Marsh/Swamp
            
        # Volcanic/Lava areas (rare)
        if random.random() < 0.05:
            possible_features.append("L")  # Lava/Volcanic
            
        # Natural resources (somewhat common)
        if random.random() < 0.15:
            possible_features.append("Q")  # Quarry/Natural resources
            
        # If no special features determined, leave empty
        if not possible_features:
            return ""
            
        # Select a random feature from the possible ones
        return random.choice(possible_features)
    
    def analyze_terrain_suitability(self, terrain_code, analysis_type="settlement_suitability"):
        """
        Analyze terrain suitability for a specific purpose.
        
        Args:
            terrain_code: 5-digit terrain code
            analysis_type: Type of analysis (settlement, agriculture, defense, trade, health)
            
        Returns:
            Suitability score (0.0 to 1.0)
        """
        if len(terrain_code) != 5:
            raise ValueError(f"Invalid terrain code: {terrain_code}. Must be 5 digits.")
            
        elevation = int(terrain_code[0])
        moisture = int(terrain_code[1])
        temperature = int(terrain_code[2])
        fertility = int(terrain_code[3])
        special = terrain_code[4] if len(terrain_code) > 4 and terrain_code[4] else ""
        
        # Get the analysis factors
        analysis_factors = self.terrain_effects["terrain_effects"].get(analysis_type, {}).get("factors", {})
        special_modifiers = self.terrain_effects["terrain_effects"].get(analysis_type, {}).get("special_feature_modifiers", {})
        
        # Apply era-specific modifiers
        era_modifiers = self.terrain_effects.get("era_specific_modifiers", {}).get(self.current_era, {})
        era_analysis_modifiers = era_modifiers.get(analysis_type, {})
        
        # Calculate base score from terrain factors
        score = 0.0
        total_weight = 0.0
        
        # Process elevation
        if "elevation" in analysis_factors:
            factor = analysis_factors["elevation"]
            weight = factor.get("weight", 0.0)
            if "weight" in era_analysis_modifiers.get("elevation", {}):
                weight = era_analysis_modifiers["elevation"]["weight"]
            
            optimal_min, optimal_max = factor.get("optimal_range", [0, 9])
            factor_score = 1.0
            
            if elevation < optimal_min and "penalty_per_level_below" in factor:
                factor_score -= factor["penalty_per_level_below"] * (optimal_min - elevation)
            elif elevation > optimal_max and "penalty_per_level_above" in factor:
                factor_score -= factor["penalty_per_level_above"] * (elevation - optimal_max)
            elif elevation > optimal_max and "bonus_per_level_above" in factor:
                factor_score += factor["bonus_per_level_above"] * (elevation - optimal_max)
                
            score += weight * max(0.0, factor_score)
            total_weight += weight
            
        # Process moisture (similar to elevation)
        if "moisture" in analysis_factors:
            factor = analysis_factors["moisture"]
            weight = factor.get("weight", 0.0)
            optimal_min, optimal_max = factor.get("optimal_range", [0, 9])
            factor_score = 1.0
            
            if moisture < optimal_min and "penalty_per_level_below" in factor:
                factor_score -= factor["penalty_per_level_below"] * (optimal_min - moisture)
            elif moisture > optimal_max and "penalty_per_level_above" in factor:
                factor_score -= factor["penalty_per_level_above"] * (moisture - optimal_max)
                
            score += weight * max(0.0, factor_score)
            total_weight += weight
            
        # Process temperature (similar pattern)
        if "temperature" in analysis_factors:
            factor = analysis_factors["temperature"]
            weight = factor.get("weight", 0.0)
            optimal_min, optimal_max = factor.get("optimal_range", [0, 9])
            factor_score = 1.0
            
            if temperature < optimal_min and "penalty_per_level_below" in factor:
                factor_score -= factor["penalty_per_level_below"] * (optimal_min - temperature)
            elif temperature > optimal_max and "penalty_per_level_above" in factor:
                factor_score -= factor["penalty_per_level_above"] * (temperature - optimal_max)
                
            score += weight * max(0.0, factor_score)
            total_weight += weight
            
        # Process fertility (similar pattern)
        if "fertility" in analysis_factors:
            factor = analysis_factors["fertility"]
            weight = factor.get("weight", 0.0)
            if "weight" in era_analysis_modifiers.get("fertility", {}):
                weight = era_analysis_modifiers["fertility"]["weight"]
                
            optimal_min, optimal_max = factor.get("optimal_range", [0, 9])
            factor_score = 1.0
            
            if fertility < optimal_min and "penalty_per_level_below" in factor:
                factor_score -= factor["penalty_per_level_below"] * (optimal_min - fertility)
                
            score += weight * max(0.0, factor_score)
            total_weight += weight
            
        # Normalize score based on weights
        if total_weight > 0:
            score = score / total_weight
            
        # Apply special feature modifier
        if special and special in special_modifiers:
            modifier = special_modifiers[special]
            
            # Check for era-specific special feature modifier
            if "special_features" in era_analysis_modifiers and special in era_analysis_modifiers["special_features"]:
                modifier = era_analysis_modifiers["special_features"][special]
                
            score += modifier
            
        # Ensure score is within bounds
        return max(0.0, min(1.0, score))
    
    def get_available_resources(self, terrain_code):
        """
        Determine available resources for a given terrain.
        
        Args:
            terrain_code: 5-digit terrain code
            
        Returns:
            Dictionary of resources and their abundance (0.0 to 1.0)
        """
        if len(terrain_code) != 5:
            raise ValueError(f"Invalid terrain code: {terrain_code}. Must be 5 digits.")
            
        elevation = int(terrain_code[0])
        moisture = int(terrain_code[1])
        temperature = int(terrain_code[2])
        fertility = int(terrain_code[3])
        special = terrain_code[4] if len(terrain_code) > 4 and terrain_code[4] else ""
        
        resources = {}
        resource_data = self.terrain_resources["resource_distribution"]
        
        for resource_name, resource_info in resource_data.items():
            # Check if resource can be found in this terrain type
            primary_terrains = resource_info["primary_terrains"]
            
            # Parse terrain ranges
            elev_range = self._parse_range(primary_terrains[0])
            moist_range = self._parse_range(primary_terrains[1])
            temp_range = self._parse_range(primary_terrains[2])
            fert_range = self._parse_range(primary_terrains[3])
            special_features = primary_terrains[4].split(",") if primary_terrains[4] else []
            
            # Check if terrain matches resource requirements
            if (self._in_range(elevation, elev_range) and 
                self._in_range(moisture, moist_range) and 
                self._in_range(temperature, temp_range) and 
                self._in_range(fertility, fert_range)):
                
                # Calculate base abundance
                abundance = 0.5  # Base value
                
                # Apply terrain modifiers
                modifiers = resource_info["abundance_modifier"]
                abundance += modifiers["elevation"] * (elevation / 9.0)
                abundance += modifiers["moisture"] * (moisture / 9.0)
                abundance += modifiers["temperature"] * (temperature / 9.0)
                abundance += modifiers["fertility"] * (fertility / 9.0)
                
                # Bonus for matching special feature
                if special and special in special_features:
                    abundance += 0.3
                
                # Apply era-specific accessibility
                accessibility = resource_info["accessibility"].get(self.current_era, 0.0)
                
                # Only include resources that are accessible in current era
                if accessibility > 0:
                    # Final abundance is base abundance * accessibility
                    resources[resource_name] = max(0.0, min(1.0, abundance)) * accessibility
        
        return resources
    
    def _parse_range(self, range_str):
        """Parse a range string like '3-7' into a tuple (3, 7)."""
        if not range_str:
            return (0, 9)  # Default to full range
        parts = range_str.split("-")
        if len(parts) == 2:
            return (int(parts[0]), int(parts[1]))
        return (int(parts[0]), int(parts[0]))  # Single value
    
    def _in_range(self, value, range_tuple):
        """Check if a value is within the specified range."""
        return range_tuple[0] <= value <= range_tuple[1]
    
    def set_current_era(self, era):
        """
        Set the current technological era for resource accessibility.
        
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
        
    def get_terrain_description(self, terrain_code):
        """
        Get a human-readable description of a terrain.
        
        Args:
            terrain_code: 5-digit terrain code
            
        Returns:
            String description of the terrain
        """
        if len(terrain_code) < 4:
            return "Unknown terrain"
            
        elevation = int(terrain_code[0])
        moisture = int(terrain_code[1])
        temperature = int(terrain_code[2])
        fertility = int(terrain_code[3])
        special = terrain_code[4] if len(terrain_code) > 4 and terrain_code[4] else ""
        
        # Get descriptions from terrain codes
        elevation_desc = self.terrain_codes["terrain_code_system"]["elevation"][str(elevation)]
        moisture_desc = self.terrain_codes["terrain_code_system"]["moisture"][str(moisture)]
        temperature_desc = self.terrain_codes["terrain_code_system"]["temperature"][str(temperature)]
        fertility_desc = self.terrain_codes["terrain_code_system"]["fertility"][str(fertility)]
        
        # Build basic description
        description = f"{elevation_desc}, {moisture_desc}, {temperature_desc} climate with {fertility_desc} soil"
        
        # Add special feature if present
        if special:
            special_desc = self.terrain_codes["terrain_code_system"]["special_features"].get(special, "Unknown feature")
            description += f", with {special_desc}"
            
        return description
    
    def find_biome_type(self, terrain_code):
        """
        Determine the biome type from a terrain code.
        
        Args:
            terrain_code: 5-digit terrain code
            
        Returns:
            String name of the biome
        """
        if len(terrain_code) < 4:
            return "unknown"
            
        elevation = int(terrain_code[0])
        moisture = int(terrain_code[1])
        temperature = int(terrain_code[2])
        fertility = int(terrain_code[3])
        special = terrain_code[4] if len(terrain_code) > 4 and terrain_code[4] else ""
        
        # Check each biome's criteria
        for biome_name, criteria in self.terrain_codes["biome_mappings"].items():
            elev_range = self._parse_range(criteria[0])
            moist_range = self._parse_range(criteria[1])
            temp_range = self._parse_range(criteria[2])
            fert_range = self._parse_range(criteria[3])
            required_special = criteria[4]
            
            if (self._in_range(elevation, elev_range) and 
                self._in_range(moisture, moist_range) and 
                self._in_range(temperature, temp_range) and 
                self._in_range(fertility, fert_range)):
                
                # If special feature is required, check it
                if required_special and special != required_special:
                    continue
                    
                return biome_name
                
        # Default biomes based on basic characteristics
        if elevation >= 4:
            return "mountain"
        if moisture <= 1:
            return "desert"
        if temperature <= 2:
            return "tundra"
        if moisture >= 7:
            return "wetland"
        if temperature >= 7 and moisture >= 6:
            return "rainforest"
        if moisture >= 5:
            return "deciduous_forest"
        if moisture >= 3:
            return "grassland"
            
        return "mixed_terrain"
