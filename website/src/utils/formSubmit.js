/**
 * Submit form data to WordPress admin-ajax.php endpoint
 * @param {FormData} formData - The form data to submit
 * @returns {Promise<Object>} Response data
 */
export async function submitForm(formData) {
    try {
        const response = await fetch('https://conduction.nl/wp-admin/admin-ajax.php', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            return {
                success: true,
                message: data.data?.message || 'Thank you for contacting us, we will be in touch shortly.',
                data: data.data
            };
        } else {
            throw new Error(data.message || 'Form submission failed');
        }
    } catch (error) {
        console.error('Form submission error:', error);
        return {
            success: false,
            message: error.message || 'An error occurred while submitting the form. Please try again.'
        };
    }
}

