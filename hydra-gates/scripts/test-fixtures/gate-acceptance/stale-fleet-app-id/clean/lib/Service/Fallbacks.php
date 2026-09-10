<?php
// Exclusion 1: prose. This comment names openconnector and OCA\Docudesk on
// purpose, and explains that /apps/openconnector/api/pdok used to be called
// from here. Explaining a rename is not committing one.

/*
 The same, in a block comment whose continuation lines start with an ordinary
 word rather than an asterisk. docudesk became filinq and decidesk became
 decidiq, and none of those words is a binding.
*/

class Fallbacks {
    // Exclusion 2: a dual-registration list. Both spellings, newest first,
    // because the other app renamed with no compatibility alias.
    private const DECISION_EVENTS = [
        'OCA\Decidiq\Event\DecisionConcludedEvent',
        'OCA\Decidesk\Event\DecisionConcludedEvent',
    ];

    // A CURRENT register slug. Both arms carry it, and it must never fire:
    // the slug rule is about slugs the owning app has MIGRATED AWAY from, not
    // about the word "register" appearing next to an app name.
    private const SOURCE_REGISTER = 'integriq';
    private const CONNECTOR_REGISTER_SLUG = 'integriq';
}
