<?php
// SPDX-License-Identifier: EUPL-1.2
//
// The engine routes what it USES of its own generics (health here) and
// nothing else: GenericDashboard is shipped for the leaf apps, which name
// its routes through Routes::standard(). `gadget#run` has no route anywhere
// and must stay a finding — the exemption is one directory, not a blanket.
return [
    'routes' => [
        ['name' => 'AppHost\Controller\GenericHealth#index', 'url' => '/api/health', 'verb' => 'GET'],
        ['name' => 'ping#index', 'url' => '/api/ping', 'verb' => 'GET'],
    ],
];
