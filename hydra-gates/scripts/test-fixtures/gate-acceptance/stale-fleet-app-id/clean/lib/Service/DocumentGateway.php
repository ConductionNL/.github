<?php
class DocumentGateway {
    private const REQUIRED_APP = 'integriq';

    public function resolve($appManager, $container) {
        if ($appManager->isInstalled(self::REQUIRED_APP) === false) {
            return null;
        }
        return $container->get('OCA\Integriq\Service\CallService');
    }
}
