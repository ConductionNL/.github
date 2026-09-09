<?php
class DocumentGateway {
    private const REQUIRED_APP = 'openconnector';

    public function resolve($appManager, $container) {
        if ($appManager->isInstalled(self::REQUIRED_APP) === false) {
            return null;
        }
        return $container->get('OCA\OpenConnector\Service\CallService');
    }
}
