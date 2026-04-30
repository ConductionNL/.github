import React, { useState } from 'react';
import styles from '../../pages/index.module.css';
import { submitForm } from '../../utils/formSubmit';


export default function ContactTeaser() {
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState(null);
  const maxMessageLength = 180;

  const handleMessageChange = (e) => {
    setMessage(e.target.value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitStatus(null);

    const formData = new FormData(e.target);

    const result = await submitForm(formData);

    setIsSubmitting(false);
    setSubmitStatus(result);

    if (result.success) {
      e.target.reset();
      setMessage('');
      setTimeout(() => setSubmitStatus(null), 5000);
    }
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
              Wij zijn ook eenvoudig met bus of tram te bereiken vanaf Station Zuid of vanaf Centraal Station uitstappen bij de halte Elandsgracht, Rozengracht of Westermarkt. Voor meer info bekijk <a href="https://9292.nl/reisinfo/9292-reisinfo-en-reisplanner" target="_blank" rel="noopener noreferrer" style={{ color: 'rgb(255, 255, 255)', textDecoration: 'underline', fontWeight: 'bold' }}>9292</a>
            </p>
          </div>
          <div className="col">
            <form className={styles.contactForm} onSubmit={handleSubmit}>
              {submitStatus && (
                <div style={{
                  padding: '10px',
                  marginBottom: '15px',
                  borderRadius: '4px',
                  backgroundColor: submitStatus.success ? '#d4edda' : '#f8d7da',
                  color: submitStatus.success ? '#155724' : '#721c24',
                  border: `1px solid ${submitStatus.success ? '#c3e6cb' : '#f5c6cb'}`
                }}>
                  {submitStatus.message}
                </div>
              )}
              <label>Naam <span className={styles.required}>*</span></label>
              <input type="text" name="name" placeholder="Bijvoorbeeld Witte de Wit" required disabled={isSubmitting} />
              <label>Uw organisatie</label>
              <input type="text" name="organization" placeholder="Gemeente de Witte Vecht" disabled={isSubmitting} />
              <label>E-mail Addres <span className={styles.required}>*</span></label>
              <input type="email" name="email" placeholder="witte@de-wit.nl" required disabled={isSubmitting} />
              <label>Telefoon nummer</label>
              <input type="tel" name="phone" placeholder="E.g. +31 123456789" disabled={isSubmitting} />
              <label>Uw bericht</label>
              <textarea name="message" placeholder="Beschrijf kort waarover u contact wilt opnemen zodat wij u zo snel mogelijk verder kunnen helpen" value={message} onChange={handleMessageChange} maxLength={maxMessageLength} disabled={isSubmitting} />
              <div className={styles.charCounter}>{message.length}/{maxMessageLength}</div>
              <button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Verzenden...' : 'Verstuur bericht'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}
