<?php
class DocumentGateway {
    private const REQUIRED_APP = 'openconnector';

    // A register slug the owning app has migrated away from: integriq ships
    // MigrateRegisterSlug mapping openconnector -> integriq. A finding, and
    // reported under its own heading because the fix is a probe rather than a
    // swap. Planted-arm ONLY: it is a defect, so it cannot sit in the file
    // both arms share.
    private const CONNECTOR_REGISTER = 'openconnector';

    public function resolve($appManager, $container) {
        if ($appManager->isInstalled(self::REQUIRED_APP) === false) {
            return null;
        }
        return $container->get('OCA\OpenConnector\Service\CallService');
    }
}
