# FICTRA Website Deployment Process

## Overview

This document outlines the deployment process for the FICTRA website, including procedures to ensure that AI-generated content is preserved during deployments. It provides a comprehensive framework for managing deployments while maintaining content integrity and site functionality.

## Deployment Principles

1. **Content Preservation** - Procedures to prevent overwrites of AI-generated content
2. **Version Control** - Clear tracking of deployed versions and changes
3. **Rollback Capability** - Ability to revert to previous versions if needed
4. **Testing Requirements** - Comprehensive testing before production deployment
5. **Documentation** - Detailed records of all deployments and changes

## Deployment Environments

The FICTRA website uses a multi-environment deployment approach:

### Development Environment

- Purpose: Active development and initial testing
- URL: dev.fictra.org
- Access: Internal team only
- Deployment Frequency: Continuous (automated)
- Content Preservation: Development content only, not production content

### Staging Environment

- Purpose: Pre-production testing and content verification
- URL: staging.fictra.org
- Access: Internal team and selected stakeholders
- Deployment Frequency: As needed for testing
- Content Preservation: Mirrors production content for testing

### Production Environment

- Purpose: Public-facing website
- URL: fictra.org
- Access: Public
- Deployment Frequency: Scheduled releases
- Content Preservation: Critical priority with specific procedures

## Content Preservation Procedures

To ensure AI-generated content is not overwritten during deployments:

1. **Content Registry**
   - Maintain a registry of AI-generated content in updates.json
   - Include file paths, last update timestamps, and content hashes
   - Automatically check for conflicts during deployment

2. **Deployment Flags**
   - Use content preservation flags in deployment configuration
   - Specify which directories and files should be preserved
   - Configure merge strategies for different content types

3. **Pre-Deployment Checks**
   - Automated verification of content integrity before deployment
   - Comparison of content registry with deployment package
   - Warning system for potential content conflicts

4. **Post-Deployment Verification**
   - Automated checks after deployment to verify content preservation
   - Visual regression testing for key pages
   - Content hash verification for critical content

## Deployment Process

The history.json file maintains a record of all deployments, including:

- Deployment timestamp and version
- Changes included in the deployment
- Deployment executor and approver
- Any issues encountered and resolutions
- Content preservation confirmations

## Maintenance Guidelines

- Update deployment history for all website deployments
- Follow content preservation procedures for every deployment
- Regularly review and update deployment processes
- Conduct post-deployment reviews to identify improvements
- Maintain clear documentation of deployment configurations

This documentation serves as the authoritative reference for FICTRA's website deployment process, ensuring that AI-generated content is preserved while maintaining site functionality and security.
