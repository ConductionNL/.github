<?php
// SPDX-License-Identifier: EUPL-1.2
//
// Routed so the controller gates treat NestedThingController as a reachable
// endpoint rather than dead code. The controller sits at lib/Controller/Api/V1/,
// which is the depth this fixture exists to reach.
return [
    'routes' => [
        ['name' => 'nestedThing#show',   'url' => '/api/v1/things/{id}', 'verb' => 'GET'],
        ['name' => 'nestedThing#adminState', 'url' => '/api/v1/admin-state', 'verb' => 'GET'],
    ],
];
