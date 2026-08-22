<?php
// SPDX-License-Identifier: EUPL-1.2

declare(strict_types=1);

namespace OCA\Fixture\AppInfo;

use OCP\AppFramework\App;
use OCP\AppFramework\Bootstrap\IBootstrap;
use OCP\AppFramework\Bootstrap\IRegistrationContext;
use Psr\Container\ContainerInterface;

/**
 * AppHost adoption WITHOUT Bootstrap::register().
 *
 * WHY AN APP DOES THIS (planix): the one-call helper also runs
 * registerServices(), which aliases the leaf's `Service\SettingsService` to the
 * engine's AppHostSettingsService. An app that ships its OWN SettingsService
 * then hands its own SettingsController the engine class and dies with a
 * TypeError on the first request. Registering the controllers and NOT the
 * services is the only shape that works there — it is adoption, spelled the
 * long way.
 */
class Application extends App implements IBootstrap
{
    public const APP_ID = 'fixture';

    public function __construct()
    {
        parent::__construct(self::APP_ID);
    }

    public function register(IRegistrationContext $context): void
    {
        $appId = self::APP_ID;

        $context->registerService(
            'OCA\\Fixture\\Controller\\DashboardController',
            static function (ContainerInterface $c) use ($appId) {
                $class = 'OCA\\OpenRegister\\AppHost\\Controller\\GenericDashboardController';
                return new $class(appName: $appId, request: $c->get('OCP\\IRequest'));
            }
        );

        $context->registerService(
            'OCA\\Fixture\\Controller\\HealthController',
            static function (ContainerInterface $c) use ($appId) {
                $class = 'OCA\\OpenRegister\\AppHost\\Controller\\GenericHealthController';
                return new $class(appName: $appId, request: $c->get('OCP\\IRequest'));
            }
        );

        $context->registerService(
            'OCA\\Fixture\\Controller\\MetricsController',
            static function (ContainerInterface $c) use ($appId) {
                $class = 'OCA\\OpenRegister\\AppHost\\Controller\\GenericMetricsController';
                return new $class(appName: $appId, request: $c->get('OCP\\IRequest'));
            }
        );

        $context->registerService(
            'OCA\\Fixture\\Controller\\PreferencesController',
            static function (ContainerInterface $c) use ($appId) {
                $class = 'OCA\\OpenRegister\\AppHost\\Controller\\GenericPreferencesController';
                return new $class(appName: $appId, request: $c->get('OCP\\IRequest'));
            }
        );
    }

    public function boot(\OCP\AppFramework\Bootstrap\IBootContext $context): void
    {
    }
}
