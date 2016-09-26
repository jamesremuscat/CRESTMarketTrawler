--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'SQL_ASCII';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: live_orders; Type: TABLE; Schema: public; Owner: eve; Tablespace: 
--

CREATE TABLE live_orders (
    orderid bigint NOT NULL,
    typeid bigint,
    regionid bigint,
    price numeric,
    volremaining integer,
    range smallint,
    volentered integer,
    minvolume integer,
    isbid boolean,
    issuedate timestamp without time zone,
    duration smallint,
    stationid bigint,
    solarsystemid bigint,
    expiry timestamp without time zone
);


ALTER TABLE public.live_orders OWNER TO eve;

--
-- Name: live_orders_priKey; Type: CONSTRAINT; Schema: public; Owner: eve; Tablespace: 
--

ALTER TABLE ONLY live_orders
    ADD CONSTRAINT "live_orders_priKey" PRIMARY KEY (orderid);


--
-- Name: cover; Type: INDEX; Schema: public; Owner: eve; Tablespace: 
--

CREATE INDEX cover ON live_orders USING btree (typeid, regionid, isbid);


--
-- Name: expiry; Type: INDEX; Schema: public; Owner: eve; Tablespace: 
--

CREATE INDEX expiry ON live_orders USING btree (expiry);


--
-- Name: live_orders_typeid; Type: INDEX; Schema: public; Owner: eve; Tablespace: 
--

CREATE INDEX live_orders_typeid ON live_orders USING btree (typeid);


--
-- Name: typeandbid; Type: INDEX; Schema: public; Owner: eve; Tablespace: 
--

CREATE INDEX typeandbid ON live_orders USING btree (typeid, isbid);


--
-- Name: typeandregion; Type: INDEX; Schema: public; Owner: eve; Tablespace: 
--

CREATE INDEX typeandregion ON live_orders USING btree (typeid, regionid);


--
-- PostgreSQL database dump complete
--

CREATE OR REPLACE FUNCTION _final_median(NUMERIC[])
   RETURNS NUMERIC AS
$$
   SELECT AVG(val)
   FROM (
     SELECT val
     FROM unnest($1) val
     ORDER BY 1
     LIMIT  2 - MOD(array_upper($1, 1), 2)
     OFFSET CEIL(array_upper($1, 1) / 2.0) - 1
   ) sub;
$$
LANGUAGE 'sql' IMMUTABLE;
 
CREATE AGGREGATE median(NUMERIC) (
  SFUNC=array_append,
  STYPE=NUMERIC[],
  FINALFUNC=_final_median,
  INITCOND='{}'
);
