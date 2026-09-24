<?php
// SPDX-License-Identifier: EUPL-1.2
//
// The store plane's two routes (portaliq's shape, WOO-559). StoreController
// is NOT shipped here and must not be: ADR-114 Decision 4 has the leaf
// declare a store and OpenRegister's GenericStoreController serve it, bound
// by Bootstrap::aliasStoreController() from the registrar below.
return [
    'routes' => [
        ['name' => 'widget#show', 'url' => '/api/widget', 'verb' => 'GET'],
        ['name' => 'store#search', 'url' => '/api/store/items', 'verb' => 'GET'],
        ['name' => 'store#install', 'url' => '/api/store/items/{slug}/install', 'verb' => 'POST'],
        // NOT the store plane and bound by nothing: a real 500 at request
        // time, and the anti-widening half of this fixture.
        ['name' => 'gadget#run', 'url' => '/api/gadget', 'verb' => 'POST'],
        // An AppHost GENERIC slug this app never wired: it calls only the
        // store plane, not Bootstrap::register(), so nothing binds
        // SettingsController. Store-plane adoption must not exempt it.
        ['name' => 'settings#index', 'url' => '/api/settings', 'verb' => 'GET'],
    ],
];
