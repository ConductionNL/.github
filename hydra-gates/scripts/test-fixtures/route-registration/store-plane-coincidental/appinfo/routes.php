<?php
// SPDX-License-Identifier: EUPL-1.2
//
// The store plane's two routes with NO engine call behind them. The
// registrar below imports Bootstrap and calls a method of the same name —
// its OWN — so both store routes are a real 500 and MUST be reported.
return [
    'routes' => [
        ['name' => 'widget#show', 'url' => '/api/widget', 'verb' => 'GET'],
        ['name' => 'store#search', 'url' => '/api/store/items', 'verb' => 'GET'],
        ['name' => 'store#install', 'url' => '/api/store/items/{slug}/install', 'verb' => 'POST'],
    ],
];
