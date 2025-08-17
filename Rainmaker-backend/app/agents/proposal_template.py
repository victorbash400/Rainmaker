"""
Modern HTML template for proposals - Apple-inspired clean design
"""

MODERN_PROPOSAL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Event Proposal - {{ client_company }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            background: #ffffff;
        }
        
        .page {
            max-width: 800px;
            margin: 0 auto;
            padding: 60px 40px;
        }
        
        /* Header - Clean SaaS Style */
        .header {
            display: flex;
            justify-content: flex-start;
            align-items: center;
            margin-bottom: 60px;
        }
        
        .logo-section {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .logo {
            width: 32px;
            height: 32px;
            background: #000000;
            border-radius: 50%;
        }
        
        .brand-name {
            font-size: 1.5rem;
            font-weight: 300;
            color: #111827;
            letter-spacing: -0.02em;
        }
        
        /* Hero Section */
        .hero {
            text-align: center;
            margin-bottom: 80px;
        }
        
        .event-proposal-badge {
            background: #111827;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1.125rem;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 32px;
            letter-spacing: 0.02em;
        }
        
        .client-name {
            font-size: 2.5rem;
            color: #111827;
            margin-bottom: 48px;
            font-weight: 600;
            letter-spacing: -0.02em;
        }
        
        .hero-details {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 24px;
            max-width: 700px;
            margin: 0 auto;
        }
        
        .hero-detail {
            text-align: center;
            padding: 20px 16px;
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }
        
        .hero-detail-label {
            font-size: 0.75rem;
            color: #9ca3af;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 500;
        }
        
        .hero-detail-value {
            font-size: 1.125rem;
            font-weight: 600;
            color: #111827;
        }
        
        /* Content Sections */
        .section {
            margin-bottom: 80px;
        }
        
        .section h2 {
            font-size: 2rem;
            font-weight: 600;
            color: #111827;
            margin-bottom: 16px;
            letter-spacing: -0.01em;
        }
        
        .section-description {
            font-size: 1.125rem;
            color: #6b7280;
            margin-bottom: 48px;
            line-height: 1.7;
        }
        
        /* Vision Section */
        .vision-text {
            font-size: 1.25rem;
            line-height: 1.8;
            color: #374151;
            margin: 32px 0;
        }
        
        /* Packages - Clean Row Layout */
        .packages {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 32px;
            margin: 48px 0;
        }
        
        .package {
            background: #ffffff;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            padding: 32px 24px;
            text-align: center;
            position: relative;
            transition: all 0.2s ease;
        }
        
        .package:hover {
            border-color: #d1d5db;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }
        
        .package.recommended {
            border-color: #111827;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        .package.recommended::before {
            content: "RECOMMENDED";
            position: absolute;
            top: -12px;
            left: 50%;
            transform: translateX(-50%);
            background: #111827;
            color: white;
            padding: 6px 16px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.05em;
        }
        
        .package-name {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 8px;
            color: #111827;
        }
        
        .package-description {
            font-size: 0.875rem;
            color: #6b7280;
            margin-bottom: 24px;
        }
        
        .package-price {
            font-size: 2.25rem;
            font-weight: 700;
            color: #111827;
            margin-bottom: 4px;
        }
        
        .package-per-person {
            font-size: 0.875rem;
            color: #9ca3af;
            margin-bottom: 24px;
        }
        
        .package-features {
            text-align: left;
            list-style: none;
        }
        
        .package-features li {
            margin: 8px 0;
            padding-left: 20px;
            position: relative;
            font-size: 0.875rem;
            color: #374151;
        }
        
        .package-features li::before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #111827;
            font-weight: 600;
        }
        
        /* Investment Summary */
        .investment-summary {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 32px;
            margin: 48px 0;
        }
        
        .investment-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .investment-table th,
        .investment-table td {
            padding: 16px 0;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }
        
        .investment-table th {
            font-weight: 600;
            color: #111827;
            font-size: 0.875rem;
        }
        
        .investment-table td {
            color: #6b7280;
            font-size: 0.875rem;
        }
        
        .investment-table .amount {
            color: #111827;
            font-weight: 600;
            text-align: right;
        }
        
        .investment-total {
            background: #111827;
            color: white;
        }
        
        .investment-total th,
        .investment-total td {
            color: white;
            padding: 20px 16px;
            border-bottom: none;
        }
        
        /* Event Details Grid */
        .details-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 24px;
            margin: 48px 0;
        }
        
        .detail-card {
            padding: 24px 20px;
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            height: fit-content;
        }
        
        .detail-icon {
            font-size: 2rem;
            margin-bottom: 16px;
        }
        
        .detail-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #111827;
            margin-bottom: 16px;
        }
        
        .detail-content p {
            margin-bottom: 12px;
            font-size: 0.875rem;
            color: #374151;
            line-height: 1.6;
        }
        
        .detail-content p:last-child {
            margin-bottom: 0;
        }
        
        .detail-content strong {
            color: #111827;
            font-weight: 600;
        }

        /* Key Requirements */
        .requirements-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 24px;
            margin: 48px 0;
        }
        
        .requirement-item {
            text-align: center;
            padding: 24px 16px;
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }
        
        .requirement-icon {
            width: 40px;
            height: 40px;
            background: #111827;
            border-radius: 50%;
            margin: 0 auto 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            color: white;
        }
        
        .requirement-title {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 8px;
            color: #111827;
        }
        
        .requirement-description {
            font-size: 0.875rem;
            color: #6b7280;
        }
        
        /* Next Steps */
        .next-steps {
            background: #111827;
            color: white;
            padding: 48px 40px;
            border-radius: 8px;
            margin: 64px 0;
        }
        
        .next-steps h3 {
            font-size: 1.75rem;
            font-weight: 600;
            margin-bottom: 16px;
            text-align: center;
        }
        
        .next-steps-intro {
            text-align: center;
            font-size: 1rem;
            opacity: 0.9;
            margin-bottom: 40px;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
            line-height: 1.6;
        }
        
        .steps-list {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 32px;
            max-width: 800px;
            margin: 0 auto;
        }
        
        .step-item {
            text-align: left;
            padding: 24px;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .step-number {
            width: 40px;
            height: 40px;
            background: rgba(255,255,255,0.15);
            border-radius: 8px;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 1rem;
        }
        
        .step-title {
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 1.125rem;
        }
        
        .step-description {
            font-size: 0.875rem;
            opacity: 0.85;
            line-height: 1.5;
        }
        
        /* Footer */
        .footer {
            margin-top: 80px;
        }
        
        .footer-container {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 40px 32px;
            text-align: center;
        }
        
        .footer h3 {
            font-size: 1.5rem;
            font-weight: 600;
            color: #111827;
            margin-bottom: 32px;
        }
        
        .contact-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 32px 24px;
            max-width: 500px;
            margin: 0 auto;
            text-align: left;
        }
        
        .contact-item {
            padding: 16px 20px;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }
        
        .contact-label {
            font-size: 0.75rem;
            color: #9ca3af;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 500;
        }
        
        .contact-value {
            font-weight: 600;
            font-size: 0.875rem;
            color: #111827;
            word-break: break-all;
        }
        
        .proposal-validity {
            margin-top: 32px;
            padding-top: 24px;
            border-top: 1px solid #e5e7eb;
            font-size: 0.875rem;
            color: #6b7280;
        }
        
        /* Print Optimizations */
        @media print {
            .page { 
                padding: 20px;
                max-width: none;
            }
            
            .header {
                margin-bottom: 40px;
                padding-bottom: 20px;
            }
            
            .hero {
                margin-bottom: 40px;
                page-break-after: avoid;
            }
            
            .section {
                margin-bottom: 40px;
                page-break-inside: avoid;
                break-inside: avoid;
            }
            
            .details-grid {
                display: block;
            }
            
            .detail-card {
                break-inside: avoid;
                page-break-inside: avoid;
                margin-bottom: 20px;
                width: 100%;
                display: block;
            }
            
            .packages {
                page-break-inside: avoid;
                break-inside: avoid;
            }
            
            .package {
                break-inside: avoid;
                page-break-inside: avoid;
                margin-bottom: 20px;
            }
            
            .investment-summary {
                page-break-inside: avoid;
                break-inside: avoid;
            }
            
            .investment-table {
                page-break-inside: avoid;
                break-inside: avoid;
            }
            
            .next-steps {
                page-break-before: auto;
                page-break-inside: avoid;
                break-inside: avoid;
                margin-top: 60px;
            }
            
            .steps-list {
                page-break-inside: avoid;
                break-inside: avoid;
            }
            
            .footer {
                page-break-before: avoid;
                margin-top: 40px;
            }
            
            /* Ensure clean page breaks */
            h2 {
                page-break-after: avoid;
                break-after: avoid;
            }
            
            .section-description {
                page-break-after: avoid;
                break-after: avoid;
            }
        }
    </style>
</head>
<body>
    <div class="page">
        <!-- Header - Clean SaaS Style -->
        <div class="header">
            <div class="logo-section">
                <div class="logo"></div>
                <div class="brand-name">Rainmaker</div>
            </div>
        </div>

        <!-- Hero Section -->
        <div class="hero">
            <div class="event-proposal-badge">Event Proposal</div>
            <div class="client-name">{{ client_company }}</div>
            <div class="hero-details">
                <div class="hero-detail">
                    <div class="hero-detail-label">Event Type</div>
                    <div class="hero-detail-value">{{ event_type }}</div>
                </div>
                <div class="hero-detail">
                    <div class="hero-detail-label">Guest Count</div>
                    <div class="hero-detail-value">{{ guest_count }}</div>
                </div>
                <div class="hero-detail">
                    <div class="hero-detail-label">Timeline</div>
                    <div class="hero-detail-value">{{ timeline }}</div>
                </div>
            </div>
        </div>
        <!-- Vision Section -->
        <div class="section">
            <h2>Event Vision</h2>
            <div class="vision-text">{{ event_vision }}</div>
        </div>

        <!-- Event Details & Logistics -->
        <div class="section">
            <h2>Event Details & Logistics</h2>
            <div class="section-description">Comprehensive planning ensures every logistical element aligns with your vision and objectives.</div>
            
            <div class="details-grid">
                <div class="detail-card">
                    <div class="detail-icon">📍</div>
                    <div class="detail-title">Location & Venue</div>
                    <div class="detail-content">
                        <p><strong>Venue Selection:</strong> We'll identify and secure the perfect venue that matches your event scale, style, and accessibility requirements.</p>
                        <p><strong>Backup Plans:</strong> Alternative venue options and contingency plans for any unforeseen circumstances.</p>
                        <p><strong>Accessibility:</strong> Full ADA compliance and accommodations for all guests.</p>
                    </div>
                </div>
                
                <div class="detail-card">
                    <div class="detail-icon">🎯</div>
                    <div class="detail-title">Event Objectives</div>
                    <div class="detail-content">
                        <p><strong>Primary Goals:</strong> {{ event_type }} focused on team building, celebration, and company culture strengthening.</p>
                        <p><strong>Success Metrics:</strong> Attendee engagement, positive feedback, and memorable experiences.</p>
                        <p><strong>Expected Outcomes:</strong> Enhanced team morale and strengthened professional relationships.</p>
                    </div>
                </div>
                
                <div class="detail-card">
                    <div class="detail-icon">👥</div>
                    <div class="detail-title">Target Audience</div>
                    <div class="detail-content">
                        <p><strong>Primary Attendees:</strong> {{ guest_count }} {{ client_company }} team members and stakeholders.</p>
                        <p><strong>Demographics:</strong> Professional workforce across all departments and seniority levels.</p>
                        <p><strong>Special Considerations:</strong> Dietary restrictions, accessibility needs, and cultural preferences.</p>
                    </div>
                </div>
                
                <div class="detail-card">
                    <div class="detail-icon">🎪</div>
                    <div class="detail-title">Setup & Layout</div>
                    <div class="detail-content">
                        <p><strong>Event Layout:</strong> Reception-style setup with designated areas for mingling, dining, and entertainment.</p>
                        <p><strong>AV Requirements:</strong> Professional sound system, lighting, and presentation equipment.</p>
                        <p><strong>Flow Design:</strong> Strategic layout ensuring smooth guest movement and engagement.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Key Requirements -->
        <div class="section">
            <h2>Key Requirements</h2>
            <div class="section-description">Based on our analysis, here are the essential elements for your event success.</div>
            <div class="requirements-grid">
                {% for requirement in key_requirements %}
                <div class="requirement-item">
                    <div class="requirement-icon">✓</div>
                    <div class="requirement-title">{{ requirement }}</div>
                    <div class="requirement-description">Carefully planned and executed to perfection</div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- Service Packages -->
        <div class="section">
            <h2>Service Packages</h2>
            <div class="section-description">Choose the perfect package tailored to your vision and requirements. Each package builds upon the previous with enhanced features and services.</div>
            
            <div class="packages">
                {% for package in packages %}
                <div class="package {% if package.recommended %}recommended{% endif %}">
                    <div class="package-name">{{ package.name }}</div>
                    <div class="package-description">{{ package.description }}</div>
                    <div class="package-price">${{ "{:,}".format(package.price) }}</div>
                    <div class="package-per-person">${{ package.per_person }} per person</div>
                    <ul class="package-features">
                        {% for feature in package.features %}
                        <li>{{ feature }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- Investment Summary -->
        <div class="section">
            <h2>Investment Breakdown</h2>
            <div class="section-description">Transparent breakdown based on our recommended Signature package, showing how your investment creates exceptional value.</div>
            
            <div class="investment-summary">
                <table class="investment-table">
                    <thead>
                        <tr>
                            <th>Service Category</th>
                            <th>Details</th>
                            <th class="amount">Investment</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Event Coordination</td>
                            <td>Full-service planning and management</td>
                            <td class="amount">${{ "{:,}".format((packages[1].price * 0.2) | int) }}</td>
                        </tr>
                        <tr>
                            <td>Venue & Logistics</td>
                            <td>Space rental and setup coordination</td>
                            <td class="amount">${{ "{:,}".format((packages[1].price * 0.25) | int) }}</td>
                        </tr>
                        <tr>
                            <td>Catering & Beverages</td>
                            <td>Premium menu with accommodations</td>
                            <td class="amount">${{ "{:,}".format((packages[1].price * 0.35) | int) }}</td>
                        </tr>
                        <tr>
                            <td>Audio/Visual & Entertainment</td>
                            <td>Professional AV and ambiance</td>
                            <td class="amount">${{ "{:,}".format((packages[1].price * 0.15) | int) }}</td>
                        </tr>
                        <tr>
                            <td>Photography & Documentation</td>
                            <td>Professional event photography</td>
                            <td class="amount">${{ "{:,}".format((packages[1].price * 0.05) | int) }}</td>
                        </tr>
                    </tbody>
                    <tfoot class="investment-total">
                        <tr>
                            <th>Total Investment</th>
                            <th>Complete Event Package</th>
                            <th>${{ "{:,}".format(packages[1].price) }}</th>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>

        <!-- Next Steps -->
        <div class="next-steps">
            <h3>Ready to Begin?</h3>
            <div class="next-steps-intro">
                Our streamlined process ensures your event planning journey is smooth, transparent, and stress-free. From initial consultation to event day execution, we're with you every step of the way.
            </div>
            <div class="steps-list">
                <div class="step-item">
                    <div class="step-number">1</div>
                    <div class="step-title">Review & Discuss</div>
                    <div class="step-description">Take time to review this proposal in detail. We'll schedule a consultation call to discuss your vision, answer questions, and explore any customizations that align with your specific goals and requirements.</div>
                </div>
                <div class="step-item">
                    <div class="step-number">2</div>
                    <div class="step-title">Finalize Agreement</div>
                    <div class="step-description">Once you're confident in our approach, we'll finalize the service agreement and secure your event date with a 50% deposit. This guarantees our team's dedicated focus on your event.</div>
                </div>
                <div class="step-item">
                    <div class="step-number">3</div>
                    <div class="step-title">Planning Kickoff</div>
                    <div class="step-description">We begin detailed planning immediately, starting with vendor selection, venue coordination, and timeline development. Your dedicated event coordinator will be your primary point of contact throughout.</div>
                </div>
                <div class="step-item">
                    <div class="step-number">4</div>
                    <div class="step-title">Flawless Execution</div>
                    <div class="step-description">On event day, our team handles every detail seamlessly. From setup to breakdown, we ensure your event runs perfectly while you focus on enjoying the experience with your guests.</div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <div class="footer-container">
                <h3>Let's Create Something Extraordinary</h3>
                <div class="contact-grid">
                    <div class="contact-item">
                        <div class="contact-label">Project Manager</div>
                        <div class="contact-value">{{ contact_info.name }}</div>
                        <div class="contact-value">{{ contact_info.title }}</div>
                    </div>
                    <div class="contact-item">
                        <div class="contact-label">Email</div>
                        <div class="contact-value">{{ contact_info.email }}</div>
                    </div>
                    <div class="contact-item">
                        <div class="contact-label">Phone</div>
                        <div class="contact-value">{{ contact_info.phone }}</div>
                    </div>
                    <div class="contact-item">
                        <div class="contact-label">Proposal ID</div>
                        <div class="contact-value">{{ proposal_id }}</div>
                    </div>
                </div>
                <div class="proposal-validity">
                    This proposal is valid until {{ valid_until_date }}
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""