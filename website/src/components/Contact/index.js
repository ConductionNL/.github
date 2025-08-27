import React, { useState } from 'react';
import styles from '../../pages/index.module.css';


export default function ContactTeaser() {
  const [message, setMessage] = useState('');
  const maxMessageLength = 180;
  const handleMessageChange = (e) => {
    setMessage(e.target.value);
  };
  return (
    <section className={styles.sectionPrimary}>
      <div className="container">
        <div className="row">
          <div className={styles.contactText}>
            <h2 className={styles.sectionTitle + ' ' + styles.sectionTitleInverted}>Contact</h2>
            <p>
              Conduction is een ICT bedrijf met een sterke idealistische en sociale inslag, waarbij mens en community centraal staan.
            </p>
            <p>
              Ons kantoor bevindt zich op een geweldige plek in het centrum van Amsterdam.
            </p>
            <p>
              Een keer langskomen of koffie drinken? Mail of bel ons. Wij zijn van maandag t/m vrijdag van 9:00 tot 17:00 bereikbaar.
            </p>
            <a href="mailto:info@conduction.nl" target="_blank" style={{ color: 'rgb(255, 255, 255)' }} rel="noopener">info@conduction.nl</a>
            <br />
            <a href="tel:+31 (0)85 3036840" style={{ color: 'rgb(255, 255, 255)' }}>+31 (0)85 3036840</a>
            <br />Lauriergracht 14h
            <br />1016 RL Amsterdam
            <br />KVK: 76741850
            <br />BTW: NL860784241B01
            <br />
            <br />
            <p>
              U kunt ons kantoor bereiken met de auto of het OV.
            </p>
            <p>
              Parkeren kan bij Q-park Marnixstraat 250, 1016 TL Amsterdam.
            </p>
            <p>
              Wij zijn ook eenvoudig met bus of tram te bereiken vanaf Station Zuid of vanaf Centraal Station uitstappen bij de halte Elandsgracht, Rozengracht of Westermarkt. Voor meer info bekijk <a href="https://9292.nl/reisinfo/9292-reisinfo-en-reisplanner" target="_blank">9292</a>
            </p>
          </div>
          <div className="col">
            <form className={styles.contactForm}>
              <label>Naam <span className={styles.required}>*</span></label>
              <input type="text" placeholder="Bijvoorbeeld Witte de Wit" required />
              <label>Uw organisatie</label>
              <input type="text" placeholder="Gemeente de Witte Vecht" />
              <label>E-mail Addres <span className={styles.required}>*</span></label>
              <input type="email" placeholder="witte@de-wit.nl" required />
              <label>Telefoon nummer</label>
              <input type="tel" placeholder="E.g. +31 123456789" />
              <label>Uw bericht</label>
              <textarea placeholder="Beschrijf kort waarover u contact wilt opnemen zodat wij u zo snel mogelijk verder kunnen helpen" value={message} onChange={handleMessageChange} maxLength={maxMessageLength} />
              <div className={styles.charCounter}>{message.length}/{maxMessageLength}</div>
              <button type="submit">Verstuur bericht</button>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}
