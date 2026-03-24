#!/bin/bash
# seed-ox.sh — Create test users and seed data in Open-Xchange
#
# Usage: bash seed-ox.sh
#
# Prerequisites:
#   - OX profile running: docker compose -f .github/docker-compose.yml --profile ox up -d
#   - Wait for OX to finish initialization (check logs: docker logs -f conduction-open-xchange)
#   - GreenMail must be running (auto-starts with ox profile)
#
# After seeding, also run seed-mail.sh to populate GreenMail with test emails.
# OX authenticates against GreenMail's IMAP, so OX users must match GreenMail accounts.

OX_CONTAINER="conduction-open-xchange"
OX_ADMIN="oxadminmaster"
OX_ADMIN_PASS="admin_master_password"
CTX_ADMIN="oxadmin"
CTX_ADMIN_PASS="oxadmin"
CTX_ID="1"

echo "=== Seeding Open-Xchange with test users ==="
echo ""

# Check if OX is running
if ! docker ps --format '{{.Names}}' | grep -q "$OX_CONTAINER"; then
    echo "ERROR: $OX_CONTAINER is not running."
    echo "Start with: docker compose -f .github/docker-compose.yml --profile ox up -d"
    exit 1
fi

# Wait for OX to be ready
echo "Checking if OX is ready..."
for i in $(seq 1 30); do
    if docker exec "$OX_CONTAINER" curl -s -o /dev/null -w "%{http_code}" http://localhost/appsuite/ 2>/dev/null | grep -q "200"; then
        echo "OX is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: OX is not ready after 5 minutes. Check logs: docker logs $OX_CONTAINER"
        exit 1
    fi
    echo "  Waiting for OX to start... ($i/30)"
    sleep 10
done

echo ""
echo "--- Creating test users ---"
echo "(Users authenticate via IMAP against GreenMail)"
echo "(GreenMail auto-creates accounts — password = email address)"
echo ""

# Create users — imaplogin must match GreenMail account (email address)
# GreenMail uses email as both username and password

create_user() {
    local username="$1"
    local display="$2"
    local given="$3"
    local surname="$4"
    local email="$5"
    local password="$6"

    docker exec "$OX_CONTAINER" /opt/open-xchange/sbin/createuser \
        -A "$CTX_ADMIN" -P "$CTX_ADMIN_PASS" -c "$CTX_ID" \
        --username "$username" \
        --displayname "$display" \
        --givenname "$given" \
        --surname "$surname" \
        --password "$password" \
        --email "$email" \
        --imaplogin "$email" \
        --language nl_NL 2>&1

    if [ $? -eq 0 ]; then
        echo "  Created user: $username ($email)"
    else
        echo "  User $username may already exist (this is OK)"
    fi
}

create_user "behandelaar" "Fatima El-Amrani" "Fatima" "El-Amrani" \
    "behandelaar@test.local" "behandelaar@test.local"

create_user "coordinator" "Noor Yilmaz" "Noor" "Yilmaz" \
    "coordinator@test.local" "coordinator@test.local"

create_user "burger" "Jan de Vries" "Jan" "de Vries" \
    "burger@test.local" "burger@test.local"

create_user "leverancier" "Mark Visser" "Mark" "Visser" \
    "leverancier@test.local" "leverancier@test.local"

create_user "admin-user" "System Admin" "System" "Admin" \
    "admin@test.local" "admin@test.local"

echo ""
echo "--- Seeding contacts and calendar via OX HTTP API ---"

# Login as behandelaar to create contacts and appointments
echo "Logging in as behandelaar..."
SESSION=$(docker exec "$OX_CONTAINER" curl -s \
    "http://localhost/ajax/login?action=login" \
    -d "name=behandelaar&password=behandelaar@test.local" \
    2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('session',''))" 2>/dev/null)

if [ -z "$SESSION" ] || [ "$SESSION" = "None" ]; then
    echo "  WARNING: Could not login as behandelaar. Skipping API seeding."
    echo "  This is expected if GreenMail hasn't received mail for this user yet."
    echo "  Run seed-mail.sh first, then retry this script."
    echo ""
    echo "=== User creation complete. Run seed-mail.sh to populate mailboxes. ==="
    exit 0
fi

echo "  Session: ${SESSION:0:16}..."

# Create contacts
echo ""
echo "Creating contacts..."

create_contact() {
    local first="$1"
    local last="$2"
    local email="$3"
    local phone="$4"
    local note="$5"

    docker exec "$OX_CONTAINER" curl -s -o /dev/null -w "%{http_code}" \
        "http://localhost/ajax/contacts?action=new&session=$SESSION" \
        -H "Content-Type: application/json" \
        -d "{
            \"folder_id\": \"con://0/6\",
            \"first_name\": \"$first\",
            \"last_name\": \"$last\",
            \"email1\": \"$email\",
            \"cellular_telephone1\": \"$phone\",
            \"note\": \"$note\"
        }" 2>/dev/null
    echo "  Contact: $first $last ($email)"
}

create_contact "Jan" "de Vries" "burger@test.local" "+31612345678" \
    "Burger - Aanvraag omgevingsvergunning dakkapel (ZK-2026-0142)"

create_contact "Priya" "Ganpat" "burger@test.local" "+31687654321" \
    "Burger - Kapvergunning (ZK-2026-0034). ZZP developer."

create_contact "Mark" "Visser" "leverancier@test.local" "+31854011580" \
    "Leverancier - Conduction B.V. Offerte REF-2026-Q1-087."

create_contact "Annemarie" "de Vries" "annemarie@vng-test.local" "+31703738393" \
    "VNG - Standaarden Architect. Common Ground / ZGW APIs."

# Create calendar appointments
echo ""
echo "Creating calendar appointments..."

# Get default calendar folder
CALENDAR_FOLDER=$(docker exec "$OX_CONTAINER" curl -s \
    "http://localhost/ajax/folders?action=list&parent=1&session=$SESSION&columns=1,300" \
    2>/dev/null | python3 -c "
import sys,json
try:
    data = json.load(sys.stdin)
    for f in data.get('data',[]):
        if 'calendar' in str(f).lower():
            print(f[0]); break
except: print('')
" 2>/dev/null)

if [ -n "$CALENDAR_FOLDER" ] && [ "$CALENDAR_FOLDER" != "" ]; then
    echo "  Using calendar folder: $CALENDAR_FOLDER"

    # Welstandscommissie meeting
    docker exec "$OX_CONTAINER" curl -s -o /dev/null \
        "http://localhost/ajax/calendar?action=new&session=$SESSION" \
        -H "Content-Type: application/json" \
        -d "{
            \"folder_id\": \"$CALENDAR_FOLDER\",
            \"title\": \"Welstandscommissie - ZK-2026-0142 (dakkapel Kerkstraat 42)\",
            \"start_date\": 1774537200000,
            \"end_date\": 1774544400000,
            \"location\": \"Raadzaal - Stadskantoor\",
            \"note\": \"Behandeling aanvraag omgevingsvergunning dakkapel.\"
        }" 2>/dev/null
    echo "  Event: Welstandscommissie"

    # IT koppeling overleg
    docker exec "$OX_CONTAINER" curl -s -o /dev/null \
        "http://localhost/ajax/calendar?action=new&session=$SESSION" \
        -H "Content-Type: application/json" \
        -d "{
            \"folder_id\": \"$CALENDAR_FOLDER\",
            \"title\": \"Overleg IT-koppelingen OpenRegister/Procest/Pipelinq\",
            \"start_date\": 1774609200000,
            \"end_date\": 1774612800000,
            \"location\": \"Online - Nextcloud Talk\",
            \"note\": \"Technisch overleg API-koppelingen en integraties.\"
        }" 2>/dev/null
    echo "  Event: IT-koppelingen overleg"
else
    echo "  WARNING: Could not find calendar folder. Skipping calendar seeding."
fi

# Logout
docker exec "$OX_CONTAINER" curl -s -o /dev/null \
    "http://localhost/ajax/login?action=logout&session=$SESSION" 2>/dev/null

echo ""
echo "=== OX seeding complete ==="
echo ""
echo "Access OX at: http://localhost:8087/appsuite"
echo ""
echo "Login credentials (authenticate via IMAP/GreenMail):"
echo "  behandelaar / behandelaar@test.local"
echo "  coordinator / coordinator@test.local"
echo "  burger / burger@test.local"
echo "  leverancier / leverancier@test.local"
echo "  admin-user / admin@test.local"
echo "  oxadmin / oxadmin (context admin)"
echo ""
echo "Next steps:"
echo "  1. Run seed-mail.sh to populate GreenMail with test emails"
echo "  2. Login to OX — mail will appear from GreenMail via IMAP"
echo "  3. Run seed-pim.sh to also populate Nextcloud contacts/calendar"
