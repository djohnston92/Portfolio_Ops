-- bronze.dim_dates_vw source

CREATE OR REPLACE VIEW bronze.dim_dates_vw
AS WITH cte AS (
         SELECT d."Date" AS date,
            d."DayLongName"::character varying(50) AS "DayLongName",
            d."MonthLongName"::character varying(50) AS "MonthLongName",
            d."MonthShortName"::character varying(50) AS "MonthShortName",
            d."CalendarDay"::integer AS "CalendarDay",
            d."CalendarWeek"::integer AS "CalendarWeek",
                CASE
                    WHEN d."Date" IS NOT NULL THEN d."Date" - EXTRACT(dow FROM d."Date")::integer + 0
                    ELSE NULL::date
                END AS "CalendarWeekStartDate",
                CASE
                    WHEN d."Date" IS NOT NULL THEN d."Date" - EXTRACT(dow FROM d."Date")::integer + 6
                    ELSE NULL::date
                END AS "CalendarWeekEndDate",
            d."CalendarDayInWeek"::integer AS "CalendarDayInWeek",
            d."CalendarMonth"::integer AS "CalendarMonth",
            d."CalendarMonthStartDate",
            d."CalendarMonthEndDate",
            d."CalendarNumberOfDaysInMonth"::integer AS "CalendarNumberOfDaysInMonth",
            d."CalendarDayInMonth"::integer AS "CalendarDayInMonth",
            d."CalendarQuarter"::integer AS "CalendarQuarter",
            d."CalendarQuarterStartDate",
            d."CalendarQuarterEndDate",
            d."CalendarNumberOfDaysInQuarter"::integer AS "CalendarNumberOfDaysInQuarter",
            d."CalendarDayInQuarter"::integer AS "CalendarDayInQuarter",
            d."CalendarYear"::integer AS "CalendarYear",
            d."CalendarYearStartDate",
            d."CalendarYearEndDate",
            d."CalendarNumberOfDaysInYear"::integer AS "CalendarNumberOfDaysInYear",
                CASE
                    WHEN d."Date" = d."CalendarWeekEndDate" THEN 1
                    ELSE 0
                END AS end_of_week_flag,
                CASE
                    WHEN d."Date" = d."CalendarMonthEndDate" THEN 1
                    ELSE 0
                END AS end_of_month_flag,
                CASE
                    WHEN d."Date" = d."CalendarQuarterEndDate" THEN 1
                    ELSE 0
                END AS end_of_qtr_flag,
                CASE
                    WHEN d."Date" = d."CalendarYearEndDate" THEN 1
                    ELSE 0
                END AS end_of_yr_flag,
                CASE
                    WHEN date_part('year'::text, d."Date") = date_part('year'::text, now()) THEN 1
                    ELSE 0
                END AS yd_ty,
                CASE
                    WHEN date_part('year'::text, d."Date") = (date_part('year'::text, now()) - 1::double precision) THEN 1
                    ELSE 0
                END AS yd_ly,
                CASE
                    WHEN date_part('year'::text, d."Date") = (date_part('year'::text, now()) - 2::double precision) THEN 1
                    ELSE 0
                END AS yd_lly,
                CASE
                    WHEN date_part('year'::text, d."Date") >= (date_part('year'::text, now()) - 2::double precision) AND d."Date" <= (now() + '2 mons'::interval) THEN 1
                    ELSE 0
                END AS regression_flag,
                CASE
                    WHEN d."Date" < now() THEN 1
                    ELSE 0
                END AS has_occured,
                CASE
                    WHEN d."Date" < CURRENT_DATE AND d."Date" >= (CURRENT_DATE - '180 days'::interval) THEN 1
                    ELSE 0
                END AS rolling_180,
                CASE
                    WHEN d."Date" < CURRENT_DATE AND d."Date" >= (CURRENT_DATE - '90 days'::interval) THEN 1
                    ELSE 0
                END AS rolling_90,
                CASE
                    WHEN d."Date" < CURRENT_DATE AND d."Date" >= (CURRENT_DATE - '30 days'::interval) THEN 1
                    ELSE 0
                END AS rolling_30,
                CASE
                    WHEN d."Date" < CURRENT_DATE AND d."Date" >= (CURRENT_DATE - '14 days'::interval) THEN 1
                    ELSE 0
                END AS rolling_14,
                CASE
                    WHEN d."Date" < CURRENT_DATE AND d."Date" >= (CURRENT_DATE - '7 days'::interval) THEN 1
                    ELSE 0
                END AS rolling_7,
                CASE
                    WHEN d."Date" < CURRENT_DATE AND d."Date" >= (CURRENT_DATE - '45 days'::interval) THEN 1
                    ELSE 0
                END AS rolling_45,
                CASE
                    WHEN d."Date" < CURRENT_DATE AND d."Date" >= (CURRENT_DATE - '365 days'::interval) THEN 1
                    ELSE 0
                END AS rolling_1_yr,
                CASE
                    WHEN d."Date" < CURRENT_DATE AND d."Date" >= (CURRENT_DATE - '730 days'::interval) THEN 1
                    ELSE 0
                END AS rolling_2_yr,
                CASE
                    WHEN d."Date" < CURRENT_DATE AND d."Date" >= (CURRENT_DATE - '1095 days'::interval) THEN 1
                    ELSE 0
                END AS rolling_3_yr
           FROM ( SELECT dimdates_production."Id",
                    dimdates_production."Date",
                    dimdates_production."DateLongDescription",
                    dimdates_production."DateShortDescription",
                    dimdates_production."DayLongName",
                    dimdates_production."DayShortName",
                    dimdates_production."MonthLongName",
                    dimdates_production."MonthShortName",
                    dimdates_production."CalendarDay",
                    dimdates_production."CalendarWeek",
                    dimdates_production."CalendarWeekStartDateId",
                    dimdates_production."CalendarWeekEndDateId",
                    dimdates_production."CalendarWeekStartDate",
                    dimdates_production."CalendarWeekEndDate",
                    dimdates_production."CalendarDayInWeek",
                    dimdates_production."CalendarMonth",
                    dimdates_production."CalendarMonthStartDateId",
                    dimdates_production."CalendarMonthEndDateId",
                    dimdates_production."CalendarMonthStartDate",
                    dimdates_production."CalendarMonthEndDate",
                    dimdates_production."CalendarNumberOfDaysInMonth",
                    dimdates_production."CalendarDayInMonth",
                    dimdates_production."CalendarQuarter",
                    dimdates_production."CalendarQuarterStartDateId",
                    dimdates_production."CalendarQuarterEndDateId",
                    dimdates_production."CalendarQuarterStartDate",
                    dimdates_production."CalendarQuarterEndDate",
                    dimdates_production."CalendarNumberOfDaysInQuarter",
                    dimdates_production."CalendarDayInQuarter",
                    dimdates_production."CalendarYear",
                    dimdates_production."CalendarYearStartDateId",
                    dimdates_production."CalendarYearEndDateId",
                    dimdates_production."CalendarYearStartDate",
                    dimdates_production."CalendarYearEndDate",
                    dimdates_production."CalendarNumberOfDaysInYear",
                    dimdates_production."FiscalDay",
                    dimdates_production."FiscalWeek",
                    dimdates_production."FiscalWeekStartDateId",
                    dimdates_production."FiscalWeekEndDateId",
                    dimdates_production."FiscalDayInWeek",
                    dimdates_production."FiscalMonth",
                    dimdates_production."FiscalMonthStartDateId",
                    dimdates_production."FiscalMonthEndDateId",
                    dimdates_production."FiscalNumberOfDaysInMonth",
                    dimdates_production."FiscalDayInMonth",
                    dimdates_production."FiscalQuarter",
                    dimdates_production."FiscalQuarterStartDateId",
                    dimdates_production."FiscalQuarterEndDateId",
                    dimdates_production."FiscalNumberOfDaysInQuarter",
                    dimdates_production."FiscalDayInQuarter",
                    dimdates_production."FiscalYear",
                    dimdates_production."FiscalYearStartDateId",
                    dimdates_production."FiscalYearEndDateId",
                    dimdates_production."FiscalNumberOfDaysInYear"
                   FROM bronze.dimdates_production) d
          ORDER BY d."Date" DESC
        ), annual AS (
         SELECT dimdates_production."CalendarDay",
            max(dimdates_production."CalendarDay") OVER (PARTITION BY dimdates_production."CalendarYearEndDate") AS max_calendar_day,
            dimdates_production."Date",
            dimdates_production."CalendarYearEndDate"
           FROM bronze.dimdates_production
        )
 SELECT a.date,
    a."DayLongName",
    a."MonthLongName",
    a."MonthShortName",
    a."CalendarDay",
    a."CalendarWeek",
    a."CalendarWeekStartDate",
    a."CalendarWeekEndDate",
    a."CalendarDayInWeek",
    a."CalendarMonth",
    a."CalendarMonthStartDate",
    a."CalendarMonthEndDate",
    a."CalendarNumberOfDaysInMonth",
    a."CalendarDayInMonth",
    a."CalendarQuarter",
    a."CalendarQuarterStartDate",
    a."CalendarQuarterEndDate",
    a."CalendarNumberOfDaysInQuarter",
    a."CalendarDayInQuarter",
    a."CalendarYear",
    a."CalendarYearStartDate",
    a."CalendarYearEndDate",
    a."CalendarNumberOfDaysInYear",
    a.end_of_week_flag,
    a.end_of_month_flag,
    a.end_of_qtr_flag,
    a.end_of_yr_flag,
    a.yd_ty,
    a.yd_ly,
    a.yd_lly,
    a.regression_flag,
    a.has_occured,
    a.rolling_90,
    a.rolling_30,
    a.rolling_14,
    a.rolling_7,
    a.rolling_45,
    a."CalendarDay"::double precision / b.max_calendar_day::double precision AS annualization_year,
    a.rolling_180,
    a.rolling_1_yr,
    a.rolling_2_yr,
    a.rolling_3_yr
   FROM cte a
     LEFT JOIN annual b ON b."Date" = a.date;