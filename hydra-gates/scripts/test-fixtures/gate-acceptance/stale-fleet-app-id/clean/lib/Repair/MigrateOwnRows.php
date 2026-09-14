<?php
// Exclusion 3: this app's OWN former id and namespace, in its own migration.
// Renaming either orphans rows this app wrote itself.
class MigrateOwnRows {
    private const OLD_APP_ID = 'procest';
    private const OLD_CLASS_PREFIX = 'OCA\\Procest\\BackgroundJob\\';
}
