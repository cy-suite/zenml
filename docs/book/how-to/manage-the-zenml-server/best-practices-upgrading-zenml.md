# Best practices for upgrading ZenML

While upgrading ZenML is generally a smooth process, there are some best practices that you should follow to ensure a successful upgrade. Based on experiences shared by ZenML users, here are some key strategies and considerations.

## Upgrading your server

Follow the tips below while upgrading your server to mitigate data losses, downtime and other issues.

### Data Backups

- **Database Backup**: Before upgrading, create a backup of your MySQL database. This allows you to rollback if necessary.
- **Automated Backups**: Consider setting up automatic daily backups of your database for added security. Most managed services like AWS RDS, Google Cloud SQL, and Azure Database for MySQL offer automated backup options.

![Screenshot of backups in AWS RDS](../../.gitbook/assets/aws-rds-backups.png)

### Upgrade Strategies

- **Staged Upgrade**: For large organizations or critical systems, consider using two ZenML server instances (old and new) and migrating services one by one to the new version.
    ![Server Migration Step 1](../../.gitbook/assets/server_migration_1.png)

    ![Server Migration Step 2](../../.gitbook/assets/server_migration_2.png)

- **Team Coordination**: If multiple teams share a ZenML server instance, coordinate the upgrade timing to minimize disruption.
- **Separate Tenants**: Coordination between teams might be difficult if one team requires new features but the other can't upgrade yet. In such cases, it is recommended to use dedicated ZenML server instances per team or product to allow for more flexible upgrade schedules.

### Minimizing Downtime

- **Upgrade Timing**: Plan upgrades during low-activity periods to minimize disruption.

- **Avoid Mid-Pipeline Upgrades**: Be cautious of automated upgrades or redeployments that might interrupt long-running pipelines.

## Upgrading your code

Sometimes, you might have to upgrade your code to work with a new version of ZenML. This is true especially when you are moving from a really old version to a new major version. The following tips might help, in addition to everything you've learnt in this document so far.

### Testing and Compatibility

- **Local Testing**: It's a good idea to update your local server first and run some old pipelines to check for compatibility issues between the old and new versions.
- **End-to-End Testing**: You can also develop simple end-to-end tests to ensure that the new version works with your pipeline code and your stack.
- **Artifact Compatibility**: Be cautious with pickle-based materializers, as they can be sensitive to changes in Python versions or libraries. Consider using version-agnostic materialization methods for critical artifacts.

### Dependency Management

- **Python Version**: Make sure that the Python version you are using is compatible with the ZenML version you are upgrading to.
- **External Dependencies**: Be mindful of external dependencies (e.g. from integrations) that might be incompatible with the new version of ZenML. This could be the case when some older versions are no longer supported or maintained and the ZenML integration is updated to use a newer version.

### Handling API Changes

While ZenML strives for backward compatibility, be prepared for occasional breaking changes (e.g., the Pydantic 2 upgrade).

- **Changelog Review**: Always review the changelog for new syntax, instructions, or breaking changes.
- **Migration Scripts**: Use provided migration scripts when available to handle database schema changes.

By following these best practices, you can minimize risks and ensure a smoother upgrade process for your ZenML server. Remember that each environment is unique, so adapt these guidelines to your specific needs and infrastructure.
