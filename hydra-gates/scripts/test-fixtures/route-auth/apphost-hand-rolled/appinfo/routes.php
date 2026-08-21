<?php
// SPDX-License-Identifier: EUPL-1.2
//
// Fixture mirroring planix: ADR-040 AppHost adoption WITHOUT the one-call
// `Bootstrap::register()` helper. The app aliases the generics itself in
// lib/AppInfo/Application.php (see the note there for why it must), so the
// dashboard/health/metrics/preferences controller files do NOT exist here.
//
// `gadget#run` is the control: it is NOT an AppHost slug and its controller is
// genuinely absent, so it must still be raised. If adoption ever loosens into
// a blanket "this app is fine" exemption, that assertion goes red here.
return [
    'routes' => [
        ['name' => 'widget#show', 'url' => '/api/widgets/{id}', 'verb' => 'GET'],

        ['name' => 'dashboard#page',    'url' => '/',            'verb' => 'GET'],
        ['name' => 'health#index',      'url' => '/api/health',  'verb' => 'GET'],
        ['name' => 'metrics#index',     'url' => '/api/metrics', 'verb' => 'GET'],
        ['name' => 'preferences#getPreference', 'url' => '/api/preferences/{key}', 'verb' => 'GET'],

        ['name' => 'gadget#run', 'url' => '/api/gadgets/run', 'verb' => 'POST'],
    ],
];
