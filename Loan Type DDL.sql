CREATE TABLE python.yield_heatmap_loan_type_presets (
	record_id uuid DEFAULT gen_random_uuid() NULL,
	loan_type text NOT NULL,
	term_options jsonb NOT NULL,
	
	principal_min numeric NOT NULL,
	principal_max numeric NOT NULL,
	
	fee_min numeric NOT NULL,
	fee_max  numeric NOT NULL,
	default_fee numeric NOT NULL,
	
	
	
	apr_min numeric NOT NULL,
	apr_max numeric NOT NULL,
	default_apr numeric NOT NULL,
	
	pd_min numeric NOT NULL,
	pd_max numeric NOT NULL,
	default_pd numeric NOT NULL,	
	
	lgd numeric NOT NULL,

	curve_type text NOT NULL,
	alias text NOT NULL,
	CONSTRAINT loan_type_presets_curve_type_chk CHECK ((curve_type = ANY (ARRAY['front_loaded'::text, 'stair_step'::text]))),
	CONSTRAINT loan_type_presets_pkey PRIMARY KEY (loan_type),
	updated_at timestamptz DEFAULT now() NOT NULL
);
