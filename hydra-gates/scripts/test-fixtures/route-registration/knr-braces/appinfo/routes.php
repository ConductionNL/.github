<?php
// SPDX-License-Identifier: EUPL-1.2
//
// Every Response-returning method in this fixture IS routed, except
// `gadget#run` — which is the anti-widening half. See the controllers.
return [
    'routes' => [
        ['name' => 'ui#dashboard', 'url' => '/', 'verb' => 'GET'],
    ],
];
