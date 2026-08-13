<?php
// SPDX-License-Identifier: EUPL-1.2
// Fixture: the anti-widening pair for `multiline-attribute`. The same
// three-line attribute, plus a SECOND routed method below it that carries
// none. Gate-5 MUST fail and MUST name `open` — stepping over a multi-line
// attribute may not let the next method borrow it.
return [
    'routes' => [
        ['name' => 'settings#save', 'url' => '/api/settings', 'verb' => 'POST'],
        ['name' => 'settings#open', 'url' => '/api/settings/{id}', 'verb' => 'GET'],
    ],
];
