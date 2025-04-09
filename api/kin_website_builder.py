#!/usr/bin/env python3
"""
Kin Website Builder

This script sets up and builds a Next.js website for a specific kin.

Usage:
    python kin_website_builder.py <blueprint> <kin_id> [--build]

Options:
    --build     Build the website after setup (default: just setup)
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_app_data_dir():
    """Get the appropriate application data directory based on the platform."""
    if os.name == 'nt':  # Windows
        app_data = 'C:\\data\\KinOS'
        logger.info(f"Using Windows path: {app_data}")
    elif os.path.exists('/data'):
        app_data = '/data/KinOS'
        logger.info(f"Using Render data directory: {app_data}")
    elif os.name == 'posix':  # Linux/Mac
        app_data = os.path.join(os.path.expanduser('~'), '.kinos')
        logger.info(f"Using Linux/Mac home directory: {app_data}")
    else:  # Fallback
        app_data = os.path.join(os.path.expanduser('~'), '.kinos')
        logger.info(f"Using fallback directory: {app_data}")
    
    return app_data

def get_blueprints_dir():
    """Get the blueprints directory."""
    app_data_dir = get_app_data_dir()
    
    # Check both possible locations (with and without v2 prefix)
    v2_blueprints_dir = os.path.join(app_data_dir, "v2", "blueprints")
    direct_blueprints_dir = os.path.join(app_data_dir, "blueprints")
    
    # Prefer v2 path if it exists and has content
    if os.path.exists(v2_blueprints_dir) and os.listdir(v2_blueprints_dir):
        logger.info(f"Using v2 blueprints directory: {v2_blueprints_dir}")
        return v2_blueprints_dir
    
    # Fall back to direct path
    logger.info(f"Using direct blueprints directory: {direct_blueprints_dir}")
    return direct_blueprints_dir

def get_kin_path(blueprint, kin_id):
    """Get the full path to a kin directory."""
    blueprints_dir = get_blueprints_dir()
    if kin_id == "template":
        return os.path.join(blueprints_dir, blueprint, "template")
    else:
        return os.path.join(blueprints_dir, blueprint, "kins", kin_id)

def setup_website_directory(kin_path):
    """
    Set up the website directory for a kin.
    
    Args:
        kin_path: Path to the kin directory
        
    Returns:
        Path to the website directory
    """
    # Create website directory
    website_dir = os.path.join(kin_path, "website")
    if os.path.exists(website_dir):
        logger.info(f"Website directory already exists: {website_dir}")
    else:
        os.makedirs(website_dir, exist_ok=True)
        logger.info(f"Created website directory: {website_dir}")
    
    return website_dir

def copy_nextjs_template(website_dir):
    """
    Copy the Next.js template to the website directory.
    
    Args:
        website_dir: Path to the website directory
        
    Returns:
        Boolean indicating success
    """
    # Path to the Next.js template
    # This should be in the script's directory under templates/nextjs
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(script_dir, "templates", "nextjs")
    
    # Check if template exists
    if not os.path.exists(template_dir):
        logger.error(f"Next.js template not found: {template_dir}")
        logger.info("Creating a basic Next.js template instead")
        
        # Create a basic Next.js template
        return create_basic_nextjs_template(website_dir)
    
    # Check if website directory is empty
    if os.listdir(website_dir):
        logger.warning(f"Website directory is not empty: {website_dir}")
        user_input = input("Website directory is not empty. Overwrite? (y/n): ")
        if user_input.lower() != 'y':
            logger.info("Aborting template copy")
            return False
        
        # Remove existing files
        for item in os.listdir(website_dir):
            item_path = os.path.join(website_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
    
    # Copy template files
    try:
        for item in os.listdir(template_dir):
            s = os.path.join(template_dir, item)
            d = os.path.join(website_dir, item)
            
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        
        logger.info(f"Successfully copied Next.js template to {website_dir}")
        return True
    except Exception as e:
        logger.error(f"Error copying template: {str(e)}")
        return False

def create_basic_nextjs_template(website_dir):
    """
    Create a basic Next.js template from scratch.
    
    Args:
        website_dir: Path to the website directory
        
    Returns:
        Boolean indicating success
    """
    try:
        # Create package.json
        package_json = {
            "name": "kin-website",
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint"
            },
            "dependencies": {
                "next": "^13.4.19",
                "react": "^18.2.0",
                "react-dom": "^18.2.0"
            }
        }
        
        with open(os.path.join(website_dir, "package.json"), 'w') as f:
            json.dump(package_json, f, indent=2)
        
        # Create next.config.js
        next_config = """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
}

module.exports = nextConfig
"""
        
        with open(os.path.join(website_dir, "next.config.js"), 'w') as f:
            f.write(next_config)
        
        # Create directories
        os.makedirs(os.path.join(website_dir, "public"), exist_ok=True)
        os.makedirs(os.path.join(website_dir, "src", "pages"), exist_ok=True)
        os.makedirs(os.path.join(website_dir, "src", "styles"), exist_ok=True)
        
        # Create index.js
        index_js = """import Head from 'next/head'
import styles from '../styles/Home.module.css'

export default function Home() {
  return (
    <div className={styles.container}>
      <Head>
        <title>Kin Website</title>
        <meta name="description" content="Generated by KinOS" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className={styles.main}>
        <h1 className={styles.title}>
          Welcome to my website!
        </h1>

        <p className={styles.description}>
          This website is managed by a KinOS AI
        </p>
      </main>

      <footer className={styles.footer}>
        <p>Powered by KinOS</p>
      </footer>
    </div>
  )
}
"""
        
        with open(os.path.join(website_dir, "src", "pages", "index.js"), 'w') as f:
            f.write(index_js)
        
        # Create _app.js
        app_js = """import '../styles/globals.css'

function MyApp({ Component, pageProps }) {
  return <Component {...pageProps} />
}

export default MyApp
"""
        
        with open(os.path.join(website_dir, "src", "pages", "_app.js"), 'w') as f:
            f.write(app_js)
        
        # Create globals.css
        globals_css = """html,
body {
  padding: 0;
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Oxygen,
    Ubuntu, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;
}

a {
  color: inherit;
  text-decoration: none;
}

* {
  box-sizing: border-box;
}
"""
        
        with open(os.path.join(website_dir, "src", "styles", "globals.css"), 'w') as f:
            f.write(globals_css)
        
        # Create Home.module.css
        home_css = """.container {
  min-height: 100vh;
  padding: 0 0.5rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.main {
  padding: 5rem 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.footer {
  width: 100%;
  height: 100px;
  border-top: 1px solid #eaeaea;
  display: flex;
  justify-content: center;
  align-items: center;
}

.title {
  margin: 0;
  line-height: 1.15;
  font-size: 4rem;
  text-align: center;
}

.description {
  line-height: 1.5;
  font-size: 1.5rem;
  text-align: center;
}
"""
        
        with open(os.path.join(website_dir, "src", "styles", "Home.module.css"), 'w') as f:
            f.write(home_css)
        
        # Create .gitignore
        gitignore = """# dependencies
/node_modules
/.pnp
.pnp.js

# testing
/coverage

# next.js
/.next/
/out/

# production
/build

# misc
.DS_Store
*.pem

# debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# local env files
.env.local
.env.development.local
.env.test.local
.env.production.local

# vercel
.vercel
"""
        
        with open(os.path.join(website_dir, ".gitignore"), 'w') as f:
            f.write(gitignore)
        
        logger.info(f"Successfully created basic Next.js template in {website_dir}")
        return True
    except Exception as e:
        logger.error(f"Error creating basic Next.js template: {str(e)}")
        return False

def build_website(website_dir):
    """
    Build the Next.js website.
    
    Args:
        website_dir: Path to the website directory
        
    Returns:
        Boolean indicating success
    """
    try:
        # Check if node_modules exists
        if not os.path.exists(os.path.join(website_dir, "node_modules")):
            logger.info("Installing dependencies...")
            subprocess.run(
                ["npm", "install"],
                cwd=website_dir,
                check=True,
                capture_output=True,
                text=True
            )
        
        # Build the website
        logger.info("Building the website...")
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=website_dir,
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info(f"Build output: {result.stdout}")
        
        # Check if build was successful
        if os.path.exists(os.path.join(website_dir, ".next")):
            logger.info("Website built successfully")
            return True
        else:
            logger.error("Build failed: .next directory not found")
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Build command failed: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error building website: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Set up and build a Next.js website for a kin")
    parser.add_argument("blueprint", help="Blueprint name")
    parser.add_argument("kin_id", help="Kin ID")
    parser.add_argument("--build", action="store_true", help="Build the website after setup")
    
    args = parser.parse_args()
    
    # Get kin path
    kin_path = get_kin_path(args.blueprint, args.kin_id)
    if not os.path.exists(kin_path):
        logger.error(f"Kin not found: {args.blueprint}/{args.kin_id}")
        return 1
    
    # Set up website directory
    website_dir = setup_website_directory(kin_path)
    
    # Copy Next.js template
    if not copy_nextjs_template(website_dir):
        logger.error("Failed to set up Next.js template")
        return 1
    
    # Build the website if requested
    if args.build:
        if not build_website(website_dir):
            logger.error("Failed to build website")
            return 1
    
    logger.info(f"Website setup complete for {args.blueprint}/{args.kin_id}")
    logger.info(f"Website directory: {website_dir}")
    
    # Print next steps
    print("\nNext steps:")
    print(f"1. Customize the website in {website_dir}")
    print("2. Build the website with: npm run build")
    print("3. Start the development server with: npm run dev")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
