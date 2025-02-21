# NEXTCon

The NEXTCon project represents an ambitious initiative to evaluate and implement Nextcloud as a comprehensive replacement for our current Microsoft 365 and Google Suite environment at Conduction. This transition aligns with our organizational values of open-source adoption and digital sovereignty, while potentially reducing our dependency on proprietary software solutions.

## Goals

- Complete phase-out of Microsoft 365 and Google Suite dependencies, moving towards a more independent and controlled digital workspace environment
- Build extensive knowledge and practical experience with Nextcloud platform implementation, focusing specifically on migration strategies and best practices for enterprise-level deployments
- Embrace the principle of "Eating your own dogfood" by actively using and testing our own solutions, which demonstrates our commitment to the technologies we recommend to clients
- Establish ourselves as a leading example in the industry for successful migration to open-source collaboration tools, inspiring other organizations to follow suit

## Out of Scope

While the project aims to be comprehensive, certain systems will remain outside its scope:

- JIRA: Project management will continue using existing tools because:
  - JIRA is deeply integrated into our development workflow and issue tracking process
  - The team has established efficient processes around JIRA (see Issue Flow documentation)
  - Migration would disrupt ongoing project tracking and agile ceremonies
  - Nextcloud's project management features don't match JIRA's specialized capabilities

- Finance: Financial systems will maintain their current infrastructure because:
  - Existing financial tools have specific compliance and regulatory requirements
  - Current systems are integrated with accounting and reporting workflows
  - Financial data security requires specialized handling
  - The cost and risk of migration outweigh potential benefits

## Google Suite Tools to Replace

Our migration strategy focuses on replacing these key Google Suite components:
- Google Meet (Meetings): Essential for daily team communications and client interactions
- Calendar: Critical for organizational scheduling and time management
- Mail: Core business communication platform
- Documents Suite:
  - Text documents: For collaborative content creation and documentation
  - Spreadsheets: For data analysis and reporting
  - Presentations: For internal and client-facing presentations
  - Draw.io: For diagram creation and visual documentation

## Other Focus Areas

Critical aspects requiring special attention during implementation:
- Rights management: Ensuring proper access control and security measures
- Authentication: Implementing robust user verification systems
- External collaboration: Maintaining seamless interaction with external partners and clients

The evaluation criteria follows a pragmatic "Good enough" approach. While we acknowledge that Nextcloud may not match every feature of Google Suite perfectly, our goal is to ensure that the platform meets our core operational requirements effectively. This realistic approach focuses on essential functionality rather than feature-for-feature parity.

## Technical Comparison

### Google Suite vs Nextcloud Features

| Feature | Google Suite | Nextcloud | Notes |
|---------|--------------|-----------|--------|
| Video Meetings | Google Meet | Talk | Max participants, screen sharing capabilities, and meeting management features |
| Calendar | Google Calendar | Calendar | Comprehensive sharing options, external invite functionality, and integration capabilities |
| Email | Gmail | Mail | Full SMTP/IMAP support with advanced filtering and organization tools |
| Document Editing | Google Docs | Collabora/OnlyOffice | Real-time collaboration features with version control and commenting |
| Storage | Google Drive | Files | Flexible storage limits with advanced sharing and permission controls |
| Authentication | Google Auth | LDAP/SSO | Multiple integration options for enterprise-level security |

## Project Plan

### Phase 1: Setup (Feb 21)
- Create dedicated namespace for the Nextcloud environment
- Set up robust technical infrastructure including backup systems and monitoring

### Phase 2: POC Period (Feb 24 - Mar 24)

Testing Team with Specialized Focus Areas:
- Remco: Leading the evaluation of core productivity tools including Documents, Spreadsheets, Calendar, and Mail functionality
- Ruben: Focusing on communication tools including Meetings, Presentations, and External Collaboration capabilities
- Mark: Conducting in-depth Technical Comparisons and analyzing Focus areas for optimization

### Phase 3: Test Migration (Mar 25 - Apr 24)

Systematic migration approach:
- Migrate email systems with minimal disruption to daily operations
- Transfer calendar data ensuring all appointments and sharing permissions are preserved
- Coordinate systematic document migration with version history maintenance

### Phase 4: Wrap-up (Apr 25 - May 24)

- Write a short blog post about the projects and lessons learned
