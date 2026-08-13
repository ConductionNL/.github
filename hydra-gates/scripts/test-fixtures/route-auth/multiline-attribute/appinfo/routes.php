<?php
// SPDX-License-Identifier: EUPL-1.2
// Fixture: one routed method whose auth attribute is written across three
// lines and sits ABOVE a long docblock. Gate-5 MUST pass — the attribute is
// there, and the length of the explanation between them is not evidence.
return [
    'routes' => [
        ['name' => 'settings#save', 'url' => '/api/settings', 'verb' => 'POST'],
    ],
];
