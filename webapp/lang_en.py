"""English texts of the interface (see webapp/i18n.py): the Czech text, which is also the message id, and its
English counterpart. `%(name)s` places must be the same in both; a literal % in a {% trans %} block is written %%.
EN: pages and messages; EN_JS: the texts of the scripts (static/*.js). tools/i18n_extract.py lists what is missing."""

EN = {
    "Účet je zrušený a tvoje data jsou smazaná.":
        "The account is closed and your data is deleted.",
    "Špatné jméno nebo heslo.":
        "Wrong name or password.",
    "Současné heslo nesedí.":
        "The current password is wrong.",
    "Heslo nesedí, účet zůstává.":
        "The password is wrong, the account stays.",
    "Registrační číslo má tvar tří písmen oddílu a čtyř číslic, např. BFM0000.":
        "A registration number is three club letters and four digits, e.g. BFM0000.",
    "Nové heslo musí mít aspoň 8 znaků.":
        "The new password must be at least 8 characters long.",
    "Heslo musí mít aspoň 8 znaků.":
        "The password must be at least 8 characters long.",
    "Nová hesla se neshodují.":
        "The new passwords do not match.",
    "Heslo je změněné.":
        "The password has been changed.",
    "Hesla se neshodují.":
        "The passwords do not match.",
    "Kód k tomuhle registračnímu číslu nesedí nebo už neplatí. Nový ti dá správce aplikace.":
        "The code for this registration number is wrong or has expired. The administrator of the app will give you a new one.",
    "Heslo je změněné. Přihlas se novým heslem.":
        "The password has been changed. Log in with the new password.",
    "Kód k tomuhle registračnímu číslu nesedí. Kód ti dá správce aplikace.":
        "The code for this registration number is wrong. The administrator of the app will give you the code.",
    "Účet s tímhle registračním číslem už existuje. Přihlas se.":
        "An account with this registration number already exists. Log in.",
    "ORIS teď neodpovídá; jméno a závody se doplní, až se ozve.":
        "ORIS is not answering right now; your name and races will be filled in when it responds.",
    "Vítej, %(name)s. Účet je založený a tvoje závody se načítají z ORIS.":
        "Welcome, %(name)s. The account has been created and your races are being loaded from ORIS.",
    "Registrační číslo %(regno)s v ORIS není.":
        "Registration number %(regno)s is not in ORIS.",
    "Neplatný formulář (CSRF), načti stránku znovu.":
        "Invalid form (CSRF), reload the page.",
    "sklon ve směru běhu (%)":
        "slope in the running direction (%)",
    "čas × proti rovině":
        "time × compared with level ground",
    "%(n)s úseků po 30 s":
        "%(n)s 30 s stretches",
    "Křivka sklonu: kolikrát déle trvá metr běhu podle sklonu":
        "Slope curve: how many times longer a metre of running takes depending on the slope",
    "referenční čas (průměr nejlepší čtvrtiny na úseku)":
        "reference time (average of the fastest quarter on the leg)",
    "ztráta na referenci":
        "loss against the reference",
    "Graf mezičasů kategorie":
        "Splits chart of the class",
    "kontrola":
        "control",
    "chyba na úseku %(n)s":
        "mistake on leg %(n)s",
    "Závody z ORIS načteny.":
        "Races loaded from ORIS.",
    "Model kopců spočítán z tvých běhů.":
        "Hill model computed from your runs.",
    "Záchytné a náběhové body u kontrol přepočítány.":
        "Relocating features and attack points of the controls recomputed.",
    "Nápověda „Ztratil jsem se“ je připravená.":
        "The “I am lost” help is ready.",
    "Účet nemá registrační číslo, závody z ORIS se nenačítaly.":
        "The account has no registration number, races were not loaded from ORIS.",
    "Na vlastní model kopců je v archivu málo běhů, zůstává výchozí.":
        "There are too few runs in the archive for your own hill model, the default stays.",
    "Mezičasy a chyby hotové. Na nejlepší postupy chybí mapa bez tratě.":
        "Splits and mistakes are done. The map without course is missing for the best routes.",
    "Zatím není co přepočítat (žádný závod s nejlepšími postupy).":
        "Nothing to recompute yet (no race with best routes).",
    "přepočítávám osobní model":
        "recomputing the personal model",
    "postupy %(i)s z %(len)s závodů (%(name)s)":
        "routes %(i)s of %(len)s races (%(name)s)",
    "Nic nového: závod už má postupy spočítané s aktuálním modelem.":
        "Nothing new: the race already has its routes computed with the current model.",
    "Nic nového: všechny %(n)s závody už mají postupy spočítané s aktuálním modelem.":
        "Nothing new: all %(n)s races already have their routes computed with the current model.",
    "Nic nového: všech %(n)s závodů už má postupy spočítané s aktuálním modelem.":
        "Nothing new: all %(n)s races already have their routes computed with the current model.",
    "čtu mapu kolem kontrol":
        "reading the map around the controls",
    "Plánované postupy oceněny modelem: %(n)s.":
        "Planned routes priced by the model: %(n)s.",
    "Žádný plánovaný postup k ocenění.":
        "No planned route to price.",
    "Mapa usazena %(how)s, odchylka %(rms).0f m, na okraji mapy asi %(edge_m).0f m.%(replaced)s Analýza je ve frontě.":
        "Map placed %(how)s, deviation %(rms).0f m, about %(edge_m).0f m at the edge of the map.%(replaced)s The analysis is queued.",
    "Zatím není z čeho model počítat (žádný závod s nejlepšími postupy).":
        "There is nothing to compute the model from yet (no race with best routes).",
    "Osobní model přepočítán.":
        "Personal model recomputed.",
    "Osobní model se nezměnil.":
        "The personal model did not change.",
    "V archivu %(seen)s souborů .fit, běhů %(added)s.":
        "%(seen)s .fit files in the archive, %(added)s runs.",
    " Smazáno %(dropped)s ostatních běhů; ty se vrátí jen opětovným nahráním exportu.":
        " Deleted %(dropped)s other runs; they come back only by uploading the export again.",
    " Spárováno se závody: %(len)s.":
        " Matched with races: %(len)s.",
    "%(e)s Závody z ORIS se nenačetly.":
        "%(e)s Races from ORIS were not loaded.",
    "ORIS teď neodpovídá, párovalo se jen se závody, které aplikace už zná: běh ze závodu, který se načte až později, nahraj znovu.":
        "ORIS is not answering right now, only races the app already knows were matched: upload a run from a race that is loaded later again.",
    "Model kopců se nestihl spočítat.":
        "The hill model could not be computed in time.",
    "Mezičasy a chyby hotové. Nejlepší postupy z fotky nepočítáme, terén se z ní nedá spolehlivě přečíst. Až pořadatel zveřejní mapu na Livelox, nahraj KMZ a přepočítá se to.":
        "Splits and mistakes are done. We do not compute best routes from a photo, the terrain cannot be read reliably from it. When the organiser publishes the map on Livelox, upload the KMZ and it will be recomputed.",
    "Kontakt":
        "Contact",
    "Analýza hotová":
        "Analysis done",
    "vzorky %(i)s z %(n)s závodů (%(name)s)":
        "samples %(i)s of %(n)s races (%(name)s)",
    "Přepočítáno %(done)s z %(n)s závodu s jedním modelem":
        "Recomputed %(done)s of %(n)s race with one model",
    "Přepočítáno %(done)s z %(n)s závodů s jedním modelem":
        "Recomputed %(done)s of %(n)s races with one model",
    "Pro tuhle kategorii už je mapa z KMZ, která je přesnější. Fotka se nepoužila.":
        "This class already has a map from a KMZ, which is more accurate. The photo was not used.",
    "Pro kategorii už je mapa ze snímku Livelox s menší odchylkou (%(course_rms).0f m); fotka (%(rms).0f m) se nepoužila.":
        "This class already has a map from a Livelox screenshot with a smaller deviation (%(course_rms).0f m); the photo (%(rms).0f m) was not used.",
    "Pro kategorii už je mapa z fotky s menší odchylkou (%(course_rms).0f m); tahle (%(rms).0f m) se nepoužila. Přepsat ji jde ručním usazením.":
        "This class already has a map from a photo with a smaller deviation (%(course_rms).0f m); this one (%(rms).0f m) was not used. It can be overwritten by placing it by hand.",
    "podle %(n)s bodů, které jsi označil":
        "by the %(n)s points you marked",
    " Nahradila předchozí mapu z fotky.":
        " It replaced the previous map from a photo.",
    "Fotka mapy se usazuje podle tvé stopy v oficiálních časech ražení: k závodu chybí běh z hodinek nebo mezičasy z ORIS. Nahraj nejdřív běh z hodinek (.fit).":
        "A photo of the map is placed using your track at the official punch times: the race has no run from the watch or no splits from ORIS. Upload the run from the watch (.fit) first.",
    "Aktivita uložena.":
        "Activity saved.",
    "Tahle aktivita už nahraná je.":
        "This activity is already uploaded.",
    " Zůstalo %(v)s běhů: %(paired)s spárovaných se závody a %(spared)s nespárovaných u závodu (v seznamu nahraných aktivit je jde přiřadit nebo smazat).":
        " %(v)s runs were kept: %(paired)s matched with races and %(spared)s unmatched at a race (in the list of uploaded activities you can assign or delete them).",
    " Zůstalo %(paired)s běhů spárovaných se závody.":
        " %(paired)s runs matched with races were kept.",
    "Plánované postupy se nepodařilo ocenit.":
        "The planned routes could not be priced.",
    ", osobní model přepočítán.":
        ", personal model recomputed.",
    " (model se změnil).":
        " (the model changed).",
    " Nahradila mapu ze snímku Livelox.":
        " It replaced the map from a Livelox screenshot.",
    "Soubor není aktivita Garmin (.fit se záznamem běhu).":
        "The file is not a Garmin activity (a .fit with a run recording).",
    " Spárováno se závodem.":
        " Matched with the race.",
    " Nově spárováno: %(len)s.":
        " Newly matched: %(len)s.",
    "Fotka k ručnímu usazení už tu není; nahraj ji znovu.":
        "The photo for manual placement is no longer there; upload it again.",
    "Soubor není zip (export účtu Garmin nebo zip se soubory .fit).":
        "The file is not a zip (a Garmin account export or a zip of .fit files).",
    "Soubor se nepodařilo otevřít jako obrázek (jpg nebo png).":
        "The file could not be opened as an image (jpg or png).",
    "Zastaveno. Hotové části zůstaly, rozpracované se zahodily.":
        "Stopped. Finished parts stayed, unfinished ones were discarded.",
    "Zastaveno.":
        "Stopped.",
    "Zastaveno, než začala.":
        "Stopped before it started.",
    "Kategorie %(name)s zůstává.":
        "The class stays %(name)s.",
    "Kategorie změněna na %(name)s. ":
        "The class was changed to %(name)s. ",
    "Závod %(name)s je v ORIS zrušený.":
        "Race %(name)s has been cancelled in ORIS.",
    "Taková kategorie u závodu není.":
        "There is no such class in the race.",
    "Závod v kategorii %(name)s už mezi svými závody máš.":
        "You already have the race in class %(name)s among your races.",
    "Oficiální čas a mezičasy jsou z jejích výsledků.":
        "The official time and splits are from its results.",
    "Ve výsledcích této kategorie v ORIS nejsi, mezičasy se vezmou z GPS.":
        "You are not in the results of this class in ORIS, the splits will be taken from the GPS.",
    "Tenhle závod už mezi svými závody máš; kategorii změníš na jeho stránce.":
        "You already have this race among your races; change the class on its page.",
    "Závod přidán v kategorii %(name)s. ":
        "Race added in class %(name)s. ",
    "Závod %(oris_id)s se z ORIS načíst nepodařilo. Je číslo závodu správně?":
        "Race %(oris_id)s could not be loaded from ORIS. Is the race number correct?",
    "Oficiální čas a mezičasy jsou z ORIS.":
        "The official time and splits are from ORIS.",
    "hledám záchytné body u kontrol":
        "looking for relocating features around the controls",
    "Výpočet (%(name)s) neskončil do %(v)s minut.":
        "The computation (%(name)s) did not finish within %(v)s minutes.",
    "Výpočet selhal (%(name)s); podrobnosti jsou níže.":
        "The computation failed (%(name)s); details are below.",
    "OpenStreetMap teď neodpovídá (přetížený server). Zakázané přechody se doplní při příštím přepočtu.":
        "OpenStreetMap is not answering right now (overloaded server). The impassable crossings will be filled in at the next recomputation.",
    "K závodu chybí aktivita (.fit) nebo mapa s tratí.":
        "The race has no activity (.fit) or no map with course.",
    "čtu trať z mapy a stopu z hodinek":
        "reading the course from the map and the track from the watch",
    "Závod nemá nejlepší postupy; záchytné body se počítají s nimi.":
        "The race has no best routes; the relocating features are computed together with them.",
    "Nápověda „Ztratil jsem se“ potřebuje mapu bez tratě i mapu s tratí.":
        "The “I am lost” help needs a map without course and a map with course.",
    "čtu terén z mapy":
        "reading the terrain from the map",
    "Záchytné body u kontrol se nepodařilo spočítat.":
        "The relocating features of the controls could not be computed.",
    "načítám výškopis":
        "loading the elevation",
    "Šrafování zakázaných prostorů se z mapy s tratí nepodařilo přečíst; postupy s ním nepočítají.":
        "The hatching of out-of-bounds areas could not be read from the map with course; the routes are computed without it.",
    "připravuji hledání postupů":
        "preparing the route search",
    "hledám nejlepší postupy: %(done)s z %(n_legs)s úseků":
        "finding the best routes: %(done)s of %(n_legs)s legs",
    "Snímek s tratí už tu není; nahraj znovu oba snímky.":
        "The screenshot with the course is no longer there; upload both screenshots again.",
    "Snímek s tratí usazen podle %(n)s z %(controls)s kontrol (odchylka %(rms).0f m); mapa s tratí z KMZ zůstává, je přesnější.":
        "The screenshot with the course was placed by %(n)s of %(controls)s controls (deviation %(rms).0f m); the map with course from the KMZ stays, it is more accurate.",
    "Mapa se mezi snímky posunula o %(max)s px, vyrovnal jsem to.":
        "The map moved by %(max)s px between the screenshots; I corrected for it.",
    "Analýza je ve frontě.":
        "The analysis is queued.",
    "Snímek se nepodařilo otevřít jako obrázek (png nebo jpg).":
        "The screenshot could not be opened as an image (png or jpg).",
    "Snímek s tratí usazen podle %(n)s z %(controls)s kontrol, odchylka %(rms).0f m.":
        "The screenshot with the course was placed by %(n)s of %(controls)s controls, deviation %(rms).0f m.",
    "Pro závod už je mapa bez tratě z KMZ, která je přesnější; snímek bez tratě se nepoužil.":
        "The race already has a map without course from a KMZ, which is more accurate; the screenshot without the course was not used.",
    " Nahradil mapu z obrázku.":
        " It replaced the map from an image.",
    " Nahradil předchozí snímek.":
        " It replaced the previous screenshot.",
    "Mapa bez tratě uložena pro celý závod (%(res)s m na pixel, přesnost asi ±%(accuracy).0f m).":
        "The map without course is saved for the whole race (%(res)s m per pixel, accuracy about ±%(accuracy).0f m).",
    " bez tratě":
        " without course",
    " Nahradila předchozí snímek.":
        " It replaced the previous screenshot.",
    "model řadí úseky stejně jako kategorie":
        "the model orders the legs the same way as the class",
    "model řadí úseky podobně jako kategorie":
        "the model orders the legs similarly to the class",
    "model řadí úseky jinak než kategorie, ber nejlepší postupy s rezervou":
        "the model orders the legs differently from the class, take the best routes with a pinch of salt",
    "kategorie tu potřebuje o %.0f %% víc času, než odpovídá modelu: model je optimistický (špatně přečtená mapa, zakázaný průchod, nebo těžká dohledávka)":
        "the class needs %.0f %% more time here than the model suggests: the model is optimistic (a wrongly read map, an out-of-bounds passage, or a hard search for the control)",
    "ztráta proti tvému normálu":
        "loss against your normal",
    "Ztráta na úsecích proti tvému normálnímu výkonu":
        "Loss on the legs against your normal performance",
    "kategorie je tu o %.0f %% rychlejší, než odpovídá modelu: model je pesimistický (terén je průběžnější, než říká mapa, nebo vede lepší postup)":
        "the class is %.0f %% faster here than the model suggests: the model is pessimistic (the terrain is more runnable than the map says, or a better route exists)",
    "Fotka je ve formátu HEIC. Ulož ji jako JPEG (v iPhonu Nastavení → Fotoaparát → Formáty → Nejkompatibilnější), nebo ji nahraj přes prohlížeč, který ji převede.":
        "The photo is in HEIC format. Save it as JPEG (on an iPhone Settings → Camera → Formats → Most Compatible), or upload it through a browser that converts it.",
    "V KMZ chybí umístění mapy (LatLonBox) nebo je obrázek příliš malý.":
        "The KMZ has no map position (LatLonBox) or the image is too small.",
    "Obrázek je příliš malý, kontroly by na něm nešly najít (aspoň 400 px na kratší straně).":
        "The image is too small, the controls could not be found on it (at least 400 px on the shorter side).",
    "Obrázek je příliš velký (nejvýš 120 megapixelů).":
        "The image is too large (at most 120 megapixels).",
    "Soubor není KMZ s mapou (export z Livelox: Share → Export → Google Earth KMZ).":
        "The file is not a KMZ with a map (Livelox export: Share → Export → Google Earth KMZ).",
    "Soubor není obrázek (jpg nebo png).":
        "The file is not an image (jpg or png).",
    "ORIS: %(total)s závodů (%(new)s nových), oficiální čas doplněn u %(with_time)s":
        "ORIS: %(total)s races (%(new)s new), official time added for %(with_time)s",
    "V profilu chybí registrační číslo ORIS.":
        "The registration number from ORIS is missing in the profile.",
    ", mezičasy kategorie načteny u %(with_class)s.":
        ", class splits loaded for %(with_class)s.",
    "Načtení závodů z ORIS":
        "Loading races from ORIS",
    "Zpracování nahraných aktivit":
        "Processing uploaded activities",
    "Analýza závodu":
        "Race analysis",
    "Přepočet osobního modelu":
        "Recomputing the personal model",
    "Usazení obrázku nebo fotky mapy":
        "Placing an image or photo of the map",
    "Ocenění plánovaného postupu":
        "Pricing a planned route",
    "Záchytné body u kontrol":
        "Relocating features of the controls",
    "Přepočítat všechno":
        "Recompute everything",
    "Nápověda „Ztratil jsem se“":
        "“I am lost” help",
    "čeká":
        "waiting",
    "běží":
        "running",
    "hotovo":
        "done",
    "%(name)s: čeká ve frontě":
        "%(name)s: waiting in the queue",
    "Úloha je znovu ve frontě.":
        "The job is queued again.",
    ", úloh před ní: %(ahead)s.":
        ", jobs ahead of it: %(ahead)s.",
    "Úloha je zastavená.":
        "The job is stopped.",
    "Úloha se zastavuje: počítaný závod se zahodí, hotové zůstanou.":
        "The job is stopping: the race being computed is discarded, finished ones stay.",
    "Zastaveno úloh: %(n)s.":
        "Jobs stopped: %(n)s.",
    "Žádná úloha nečeká ani neběží.":
        "No job is waiting or running.",
    "Čára je smazaná, postupy se přepočítají všem, kdo závod běželi.":
        "The line is deleted, the routes will be recomputed for everyone who ran the race.",
    "%(name)s: od tebe %(dist)s m na azimut %(az)s, od kontroly %(cdist)s m na azimut %(caz)s":
        "%(name)s: %(dist)s m from you on bearing %(az)s, %(cdist)s m from the control on bearing %(caz)s",
    " (nešlo minout)":
        " (you could not miss it)",
    " (trefil bys ji z %(share)s %% kruhu)":
        " (you would have hit it from %(share)s %% of the circle)",
    "cesta, silnice":
        "path, road",
    "louka":
        "meadow",
    "hrubá louka":
        "rough meadow",
    "les (dobře průběžný)":
        "forest (easily runnable)",
    "podrost (zelené šrafy)":
        "undergrowth (green stripes)",
    "světle zelená (pomalý běh)":
        "light green (slow running)",
    "bažina":
        "marsh",
    "zelená (chůze)":
        "green (walking)",
    "tmavě zelená (prodírání)":
        "dark green (fighting through)",
    "%(where)s jsi %(better)s než průměr":
        "%(where)s you are %(better)s than average",
    "rychlejší":
        "faster",
    "pomalejší":
        "slower",
    "do kopce jsi %(better)s než průměr":
        "uphill you are %(better)s than average",
    "z kopce jsi %(better)s než průměr":
        "downhill you are %(better)s than average",
    "v terénu":
        "in rough terrain",
    "Přepočítat všechno je ve frontě: postup uvidíš v seznamu úloh.":
        "Recompute everything is queued: you can follow it in the list of jobs.",
    "Přepočet osobního modelu je ve frontě.":
        "Recomputing the personal model is queued.",
    "Fotka se usazuje podle tvých bodů na pozadí. Až bude hotová, analýza kategorie se spustí znovu.":
        "The photo is being placed by your points in the background. When it is done, the analysis of the class runs again.",
    "Mapa by se posunula o %(shift_m).0f m a otočila o %(abs).1f° (měřítko %(scale_pct)+.1f %%); body pak sedí na %(rms).0f m.":
        "The map would move by %(shift_m).0f m and turn by %(abs).1f° (scale %(scale_pct)+.1f %%); the points would then fit within %(rms).0f m.",
    "Mapa posunutá o %(shift_m).0f m a otočená o %(turn).1f° (%(n)s mapa). Analýzy závodu se pustí znovu.":
        "Map moved by %(shift_m).0f m and turned by %(turn).1f° (%(n)s map). The analyses of the race run again.",
    "Mapa posunutá o %(shift_m).0f m a otočená o %(turn).1f° (%(n)s mapy). Analýzy závodu se pustí znovu.":
        "Map moved by %(shift_m).0f m and turned by %(turn).1f° (%(n)s maps). The analyses of the race run again.",
    "Mapa posunutá o %(shift_m).0f m a otočená o %(turn).1f° (%(n)s map). Analýzy závodu se pustí znovu.":
        "Map moved by %(shift_m).0f m and turned by %(turn).1f° (%(n)s maps). The analyses of the race run again.",
    "Snímky se usazují znovu s mapou, jak jsi ji ořízl. Výsledek uvidíš v úlohách.":
        "The screenshots are being placed again with the map as you cropped it. You will see the result in the jobs.",
    "K závodu není uložená žádná fotka mapy. Nahraj ji v Podkladech (pole Mapa s tratí).":
        "There is no photo of the map saved for the race. Upload it in Source files (the field Map with course).",
    "Označ aspoň %(MIN_POINTS)s kontroly, co nejdál od sebe.":
        "Mark at least %(MIN_POINTS)s controls, as far from each other as possible.",
    "Bod %(n)s je o %(v)s m jinde, než kam ho dávají ostatní: asi je na jiné kontrole.":
        "Point %(n)s is %(v)s m away from where the others put it: it is probably on another control.",
    "Mapy jsou zpět, jak byly nahrané. Analýzy závodu se pustí znovu.":
        "The maps are back as they were uploaded. The analyses of the race run again.",
    "Nebylo co vracet.":
        "There was nothing to restore.",
    "Obdélník je moc malý. Natáhni ho přes celou mapu (bez lišty a tlačítek Livelox).":
        "The rectangle is too small. Stretch it over the whole map (without the bar and the Livelox buttons).",
    "Označ aspoň %(MIN_POINTS)s kontroly.":
        "Mark at least %(MIN_POINTS)s controls.",
    "zakázáno":
        "impassable",
    "jen znevýhodněno":
        "only penalised",
    "nepoužívat":
        "do not use",
    "připraveno":
        "ready",
    "Načítám závody z ORIS, za chvíli se objeví.":
        "Loading races from ORIS, they will appear in a moment.",
    "Snímky jsou nahrané. Usazují se na pozadí podle kontrol a tvé stopy; výsledek uvidíš v úlohách.":
        "The screenshots are uploaded. They are being placed in the background by the controls and your track; you will see the result in the jobs.",
    "analýza selhala":
        "analysis failed",
    "zastaveno":
        "stopped",
    "chybí aktivita":
        "activity missing",
    "chybí mapa bez tratě":
        "map without course missing",
    "chybí mapa":
        "map missing",
    "Tenhle účet nemá registrační číslo ORIS, závody z něj načíst nejde. Přidej závod ručně.":
        "This account has no ORIS registration number, so races cannot be loaded for it. Add a race by hand.",
    "Nastavení se nezměnilo.":
        "The settings did not change.",
    "Obrázek je nahraný. Usazuje se na pozadí podle kontrol a tvé stopy; výsledek uvidíš v úlohách.":
        "The image is uploaded. It is being placed in the background by the controls and your track; you will see the result in the jobs.",
    "Snímek z Livelox se usazuje podle tvé stopy v oficiálních časech ražení: k závodu chybí běh z hodinek nebo mezičasy z ORIS. Nahraj nejdřív běh z hodinek (.fit), nebo použij KMZ z Livelox.":
        "A Livelox screenshot is placed by your track at the official punch times: the race has no run from the watch or no splits from ORIS. Upload the run from the watch (.fit) first, or use a KMZ from Livelox.",
    "Snímek bez tratě se usazuje podle snímku s tratí ze stejného pohledu. Nahraj nejdřív oba snímky najednou (nebo mapu bez tratě jako KMZ z Livelox).":
        "A screenshot without the course is placed by the screenshot with the course from the same view. Upload both screenshots at once first (or the map without course as a KMZ from Livelox).",
    "Pro závod už je mapa bez tratě z KMZ, která je přesnější. Snímek bez tratě se nepoužil.":
        "The race already has a map without course from a KMZ, which is more accurate. The screenshot without the course was not used.",
    "Vyber aspoň jeden soubor.":
        "Choose at least one file.",
    "Záchytné body se počítají až s nejlepšími postupy (chybí mapa bez tratě nebo analýza).":
        "The relocating features are computed only together with the best routes (the map without course or the analysis is missing).",
    "Záchytné body se přepočítávají, za chvíli se objeví.":
        "The relocating features are being recomputed, they will appear in a moment.",
    "K analýze chybí běh (.fit) nebo mapa s tratí.":
        "The analysis lacks the run (.fit) or the map with course.",
    "Analýza je zařazená do fronty.":
        "The analysis is queued.",
    "Uloženo.":
        "Saved.",
    "počítá se":
        "being computed",
    "čeká ve frontě":
        "waiting in the queue",
    "Vyplň název, datum (RRRR-MM-DD) a čas jako 55:07 nebo 1:20:18 (čas může zůstat prázdný).":
        "Fill in the name, the date (YYYY-MM-DD) and the time like 55:07 or 1:20:18 (the time may stay empty).",
    "Zadej číslo závodu v ORIS (např. 9827) nebo odkaz na něj (…/Zavod?id=9827).":
        "Enter the race number in ORIS (e.g. 9827) or a link to it (…/Zavod?id=9827).",
    "Kategorie závodu jsou načtené z ORIS.":
        "The classes of the race are loaded from ORIS.",
    "Obrázek jde nahrát jen jako mapu s tratí (usazuje se podle kontrol). Mapu bez tratě nahraj jako KMZ z Livelox.":
        "An image can be uploaded only as a map with course (it is placed by the controls). Upload the map without course as a KMZ from Livelox.",
    "Obrázek nebo fotka mapy se usazuje podle tvé stopy v oficiálních časech ražení: k závodu chybí běh z hodinek nebo mezičasy z ORIS. Nahraj nejdřív běh z hodinek (.fit), nebo použij KMZ z Livelox.":
        "An image or photo of the map is placed by your track at the official punch times: the race has no run from the watch or no splits from ORIS. Upload the run from the watch (.fit) first, or use a KMZ from Livelox.",
    "Mapa bez tratě je uložená pro všechny, kdo tenhle závod běželi.":
        "The map without course is saved for everyone who ran this race.",
    "Mapa s tratí je uložená pro kategorii %(class_name)s.":
        "The map with course is saved for the class %(class_name)s.",
    "%(filename)s: snímek obrazovky má být obrázek (png nebo jpg).":
        "%(filename)s: the screenshot must be an image (png or jpg).",
    "%(filename)s: není aktivita Garmin (.fit se záznamem běhu, nebo zip s jedním .fit). Celý export z Garminu nahraj v Nahrát běhy.":
        "%(filename)s: not a Garmin activity (a .fit with a run recording, or a zip with one .fit). Upload a whole Garmin export in Upload runs.",
    "Běh je nahraný a spárovaný s tímhle závodem.":
        "The run is uploaded and matched with this race.",
    "Vítej! Zadej svoje registrační číslo ORIS, načtou se z něj tvoje závody. Jde to i později, nebo to přeskoč a přidávej závody ručně.":
        "Welcome! Enter your ORIS registration number and your races will be loaded from it. You can also do it "
        "later, or skip it and add races by hand.",
    "Uloženo. Závody z ORIS se načítají (%(name)s).":
        "Saved. Races are being loaded from ORIS (%(name)s).",
    " Postupy se přepočítají na pozadí.":
        " The routes will be recomputed in the background.",
    " Nahradila mapu ze snímku Livelox; nejlepší postupy se přepočítají.":
        " It replaced the map from a Livelox screenshot; the best routes will be recomputed.",
    " Nahradila mapu z fotky; analýza všech běžců kategorie se spustí znovu.":
        " It replaced the map from a photo; the analysis of all runners of the class runs again.",
    " Nahradila mapu ze snímku Livelox; analýza všech běžců kategorie se spustí znovu.":
        " It replaced the map from a Livelox screenshot; the analysis of all runners of the class runs again.",
    "ORIS teď neodpovídá, zkus registrační číslo uložit později.":
        "ORIS is not answering right now, try saving the registration number later.",
    "Běh je spárovaný se závodem. Nejdřív u závodu vyber jiný běh.":
        "The run is matched with a race. First choose another run for the race.",
    "Běh je smazaný.":
        "The run is deleted.",
    "Nahráno souborů: %(n)s. Zpracují se na pozadí a samy se spárují se závody.":
        "Files uploaded: %(n)s. They are processed in the background and matched with races on their own.",
    "%(filename)s: nahrát jde jen .fit nebo .zip.":
        "%(filename)s: only .fit or .zip can be uploaded.",
    "Znovu přečte vzorky stop, jednou přepočítá model a s ním postupy všech závodů, jeden po druhém":
        "Reads the track samples again, recomputes the model once and with it the routes of all races, one by one",
    "Uložit moje nastavení a přepočítat postupy":
        "Save my settings and recompute the routes",
    "Platí jen pro tvůj rozbor: ostatním, kdo závod běželi, se nic nepřepočítá.":
        "Applies only to your analysis: nothing is recomputed for the others who ran the race.",
    "Železnice a dálnice":
        "Railways and motorways",
    "Trať železnice, dálnice a silnice pro motorová vozidla se berou z OpenStreetMap. Přejezdy, mosty a podchody zůstávají průchozí.":
        "Railways, motorways and roads for motor vehicles are taken from OpenStreetMap. Level crossings, bridges and underpasses stay passable.",
    "jako závod":
        "as the race",
    "výchozí nastavení závodu, teď „%(mode)s“":
        "default setting of the race, now “%(mode)s”",
    "postup přes ně nikdy nevede (jen přejezdem, mostem nebo podchodem)":
        "a route never goes across them (only by a level crossing, a bridge or an underpass)",
    "jde je překonat kdekoli, ale stojí to hodně času":
        "they can be crossed anywhere, but it costs a lot of time",
    "překážky z OpenStreetMap se v mém rozboru ignorují":
        "obstacles from OpenStreetMap are ignored in my analysis",
    "Staženo %(fetched)s: %(lines)s úseků překážek, %(crossings)s přechodů. Zdroj: © přispěvatelé OpenStreetMap, licence ODbL.":
        "Downloaded %(fetched)s: %(lines)s stretches of obstacles, %(crossings)s crossings. Source: © OpenStreetMap contributors, ODbL licence.",
    "Stahování z OpenStreetMap je v této instalaci vypnuté (<code>OB_OSM=0</code>).":
        "Downloading from OpenStreetMap is switched off in this installation (<code>OB_OSM=0</code>).",
    "Překážky se stáhnou při první analýze s mapou bez tratě.":
        "The obstacles are downloaded at the first analysis with the map without course.",
    "Překážky se stáhnou při příští analýze závodu.":
        "The obstacles are downloaded at the next analysis of the race.",
    "Zakázané prostory z mapy":
        "Out-of-bounds areas from the map",
    "Fialové šrafování (zakázaný prostor) se čte z mapy s tratí. Postup do něj nevede a v mapě je vybarvený. Prostory se čtou z mapy každé kategorie zvlášť.":
        "Purple hatching (an out-of-bounds area) is read from the map with course. Routes do not enter it and it is coloured on the map. The areas are read from the map of each class separately.",
    "postup se šrafovanému prostoru vyhne":
        "routes avoid the hatched area",
    "šrafování se v mém rozboru ignoruje (třeba když se přečetlo špatně)":
        "hatching is ignored in my analysis (e.g. when it was read wrongly)",
    "Přečteno %(read)s z tvé mapy s tratí:":
        "Read %(read)s from your map with course:",
    "zakázaných prostorů %(n)s.":
        "out-of-bounds areas: %(n)s.",
    "žádné šrafování na ní není.":
        "there is no hatching on it.",
    "Čte se křížové šrafování a šrafy ze svislých rovnoběžných čar; zakázanou hranici (jednu čáru) nakresli ručně.":
        "Cross hatching and hatching of vertical parallel lines are read; draw an impassable boundary (a single line) by hand.",
    "Šrafování se přečte z mapy s tratí, až ji někdo nahraje.":
        "The hatching is read from the map with course once somebody uploads it.",
    "Šrafování se přečte při první analýze s mapou bez tratě.":
        "The hatching is read at the first analysis with the map without course.",
    "Šrafování se přečte při příští analýze závodu.":
        "The hatching is read at the next analysis of the race.",
    "Výchozí nastavení závodu":
        "Default setting of the race",
    "Platí pro každého, kdo si výše nezvolil vlastní. Změnit ho může jen ten, kdo nahrál mapu bez tratě (%(who)s); přepočítají se pak jen běžci bez vlastního nastavení.":
        "Applies to everyone who did not choose their own above. Only the one who uploaded the map without course can change it (%(who)s); only runners without their own setting are then recomputed.",
    "Platí pro každého, kdo si výše nezvolil vlastní. Změnit ho může jen ten, kdo nahrál mapu bez tratě; přepočítají se pak jen běžci bez vlastního nastavení.":
        "Applies to everyone who did not choose their own above. Only the one who uploaded the map without course can change it; only runners without their own setting are then recomputed.",
    "Uložit výchozí nastavení závodu":
        "Save the default setting of the race",
    "Ruční zakázané čáry":
        "Impassable lines drawn by hand",
    "Plot, zakázaný prostor nebo trať, kterou OpenStreetMap nezná: nakresli čáru do mapy. Postup ji nesmí překročit. Čára je sdílená pro všechny běžce závodu a přepočítá postupy všem; smazat ji může jen ten, kdo ji nakreslil.":
        "A fence, an out-of-bounds area or a line that OpenStreetMap does not know: draw a line on the map. Routes must not cross it. The line is shared by all runners of the race and recomputes the routes for all of them; only the one who drew it can delete it.",
    "Nakreslit zakázanou čáru":
        "Draw an impassable line",
    "Nakreslit těžko překonatelnou čáru":
        "Draw a hardly passable line",
    "Kreslit jde, až bude závod analyzovaný (mapa s tratí a běh z hodinek).":
        "You can draw once the race is analysed (a map with course and a run from the watch).",
    "Čára":
        "Line",
    "Druh":
        "Kind",
    "Délka":
        "Length",
    "Přidal":
        "Added by",
    "těžko překonatelná":
        "hardly passable",
    "zakázaná":
        "impassable",
    "zrušený účet":
        "deleted account",
    "Smazat":
        "Delete",
    "Zatím žádná.":
        "None yet.",
    "„Zakázaná“ znamená zákaz (nekonečná cena, ISOM 708 a 709). „Těžko překonatelná“ není zákaz, jen velká ztráta času (nepřekonatelný sráz, hustý plot): postup ji překročí, jen když se to hodně vyplatí.":
        "“Impassable” means a ban (infinite cost, ISOM 708 and 709). “Hardly passable” is not a ban, just a big loss of time (an impassable cliff, a thick fence): a route crosses it only when it pays off a lot.",
    "Občerstvovačka":
        "Refreshment control",
    "Zastávky do 30 m od značky se berou jako záměrné automaticky, všem běžcům závodu. Smazat ji může jen ten, kdo ji přidal (kliknutím na značku „O“ v mapě).":
        "Stops within 30 m of the mark count as deliberate automatically, for all runners of the race. Only the one who added it can delete it (by clicking the “O” mark on the map).",
    "Přidat občerstvovačku":
        "Add a refreshment control",
    "občerstvovačka %(n)s: přidal %(who)s":
        "refreshment control %(n)s: added by %(who)s",
    "Mezičasy kategorie":
        "Class splits",
    "Oficiální mezičasy %(n)s běžců kategorie %(cls)s z ORIS (%(ok)s klasifikovaných). Počítá se jen z časů, bez mapy a bez stopy z hodinek.":
        "Official splits of %(n)s runners of class %(cls)s from ORIS (%(ok)s classified). Computed from times only, without the map and without the track from the watch.",
    "Tvůj výkon":
        "Your performance",
    "Čas":
        "Time",
    "neklasifikován":
        "not classified",
    "%(place)s. místo":
        "place %(place)s",
    "Normální výkon":
        "Normal performance",
    "<b>%(pct)s %%</b> reference":
        "<b>%(pct)s %%</b> of the reference",
    "Chyby":
        "Mistakes",
    "dohromady %(total)s":
        "%(total)s in total",
    "Čas bez chyb":
        "Time without mistakes",
    "Vítěz":
        "Winner",
    "Součet nejlepších úseků":
        "Sum of the best legs",
    "V mezičasech kategorie tě ORIS pod tvým registračním číslem nemá (jiná kategorie, nebo závod bez čipu).":
        "ORIS does not have you in the splits of the class under your registration number (another class, or a race without a chip).",
    "Jak to číst":
        "How to read it",
    "<b>Reference</b> úseku je průměr nejrychlejší čtvrtiny běžců na tom úseku. <b>Normální výkon</b> je tvoje obvyklé tempo proti referenci (medián přes úseky, 100 %% = jako reference).":
        "The <b>reference</b> of a leg is the average of the fastest quarter of runners on that leg. <b>Normal performance</b> is your usual pace against the reference (the median over the legs, 100 %% = like the reference).",
    "<b>Jak se pozná chyba.</b> U ostatních běžců jen z mezičasů: chyba je úsek, kde byl běžec o víc než 30 s a zároveň o víc než 25 %% pomalejší než jeho vlastní normál (metoda WinSplits). Pomalý běh celý závod tedy chybou není, jeden pomalý úsek být může. U tebe má appka i stopu z hodinek, a tak na záložce Mapa a úseky pozná i druh chyby (přeběhnutí, nedoběhnutí, úhyb ze směru, hledání v kruhu, zastavení a nové určení polohy). Pozdější startovní čas pomáhá (vyšlapané stopy), takže malé rozdíly neznamenají chybu.":
        "<b>How a mistake is recognised.</b> For the other runners from splits only: a mistake is a leg where the runner was more than 30 s and at the same time more than 25 %% slower than their own normal (the WinSplits method). Running slowly the whole race is therefore not a mistake, a single slow leg may be. For you the app also has the track from the watch, so on the tab Map and legs it recognises the kind of mistake too (overshooting, falling short, drifting off line, searching in circles, stopping to relocate). A later start time helps (trodden tracks), so small differences do not mean a mistake.",
    "Graf mezičasů":
        "Splits chart",
    "Každá čára je jeden běžec. Zelená jsi ty. Vodorovně je postup tratí, svisle o kolik je běžec před (nahoře) nebo za (dole) referencí. Klesá-li čára, běžec na úseku ztrácí; stoupá-li, je na úseku rychlejší než reference. Reference úseku je průměr nejrychlejší čtvrtiny běžců na tom úseku. Čísla nad grafem jsou kontroly, červené body tvoje chyby. Najeď na čáru myší (na telefonu na ni ťukni): ukáže se jméno a ztráta v tom místě.":
        "Each line is one runner. Green is you. Horizontally is the progress along the course, vertically how far the runner is ahead of (up) or behind (down) the reference. When the line falls, the runner is losing on the leg; when it rises, the runner is faster on the leg than the reference. The reference of a leg is the average of the fastest quarter of runners on that leg. The numbers above the chart are the controls, the red points are your mistakes. Hover over a line (on a phone tap it): the name and the loss at that place appear.",
    "Ztráta po úsecích proti tvému normálu (čím menší, tím lepší)":
        "Loss on the legs against your normal (the smaller the better)",
    "Úseky podle mezičasů":
        "Legs by splits",
    "Úsek":
        "Leg",
    "Kontrola":
        "Control",
    "Tvůj čas":
        "Your time",
    "Pořadí":
        "Place",
    "Reference úseku je průměr nejrychlejší čtvrtiny běžců na tom úseku.":
        "The reference of a leg is the average of the fastest quarter of runners on that leg.",
    "Reference":
        "Reference",
    "Nejlepší":
        "Best",
    "Výkon":
        "Performance",
    "Očekávaný čas":
        "Expected time",
    "Ztráta":
        "Loss",
    "Chyba":
        "Mistake",
    "chyba":
        "mistake",
    "Jak dobře model rychlosti sedí s kategorií (kontrola modelu, ne rada pro běh) je na <a href=\"%(url)s#jak-sedi\">stránce modelu</a>.":
        "How well the speed model agrees with the class (a check of the model, not advice for running) is on the <a href=\"%(url)s#jak-sedi\">model page</a>.",
    "Běžci kategorie":
        "Runners of the class",
    "Místo":
        "Place",
    "Jméno":
        "Name",
    "Oddíl":
        "Club",
    "Normál":
        "Normal",
    "Chyb":
        "Mistakes",
    "Ztraceno chybami":
        "Lost to mistakes",
    "Sloupce Normál, Chyb a Ztraceno chybami se počítají pro každého běžce stejnou metodou z veřejných mezičasů ORIS (proto je mají i ostatní). <b>Normál</b> je tvoje obvyklé tempo proti referenci, 100 %% = jako reference. Výsledky a mezičasy jsou veřejné údaje z ORIS. Stopy z hodinek ostatních běžců aplikace neukazuje.":
        "The columns Normal, Mistakes and Lost to mistakes are computed for every runner by the same method from the public ORIS splits (so the others have them too). <b>Normal</b> is your usual pace against the reference, 100 %% = like the reference. Results and splits are public data from ORIS. The app does not show the tracks from the watches of other runners.",
    "O aplikaci a omezení":
        "About the app and its limits",
    "Jak to celé funguje a co model (zatím) nedokáže.":
        "How it all works and what the model cannot do (yet).",
    "Jak to funguje":
        "How it works",
    "Mřížka 2,7 × 2,7 m":
        "Grid 2.7 × 2.7 m",
    "Mapu z Livelox rozdělí na čtvercová políčka a z barev mapy přečte, jaký terén v každém leží (cesta, louka, les, podrost, zelená, voda).":
        "The map from Livelox is divided into square cells and the colours of the map tell what terrain lies in each (path, meadow, forest, undergrowth, green, water).",
    "Ohodnocení v sekundách":
        "Rating in seconds",
    "Každé políčko dostane cenu podle terénu, sklonu z výškopisu a tvého osobního modelu rychlosti.":
        "Each cell gets a cost by its terrain, the slope from the elevation data and your personal speed model.",
    "Výpočet bez AI":
        "Calculation without AI",
    "Najde trasu s nejmenším součtem časů, jako navigace přes les. Žádná umělá inteligence nic nehádá: počítá geometrie, mřížka a tvůj model.":
        "It finds the route with the smallest sum of times, like a navigation system through the forest. No artificial intelligence guesses anything: geometry, the grid and your model do the computing.",
    "Zdroje dat":
        "Data sources",
    "tvoje stopa":
        "your track",
    "mapa a trať":
        "map and course",
    "výsledky a mezičasy":
        "results and splits",
    "ČÚZK, AWS":
        "ČÚZK, AWS",
    "výškopis":
        "elevation",
    "Omezení modelu":
        "Limits of the model",
    "Limitace modelu":
        "Limits of the model",
    "Pozor":
        "Caution",
    "Zná jen tebe a závody, které nahraješ (malý vzorek).":
        "It knows only you and the races you upload (a small sample).",
    "Skály, srázy a detaily na mapě z Livelox nepřečte.":
        "It cannot read cliffs, steep slopes and details on a map from Livelox.",
    "Sprintové mapy a zakázané prostory jsou jen částečně ověřené.":
        "Sprint maps and out-of-bounds areas are only partly verified.",
    "Neví, co se běžci honilo hlavou při chybách.":
        "It does not know what was going through the runner's head when making mistakes.",
    "Lokální zpracování · data zůstávají u tebe":
        "Local processing · the data stays with you",
    "Zdarma":
        "Free",
    "Autor":
        "Author",
    "Jak na to":
        "How to",
    "verze %(version)s":
        "version %(version)s",
    "Rozbor postupů":
        "Route analysis",
    "Přehled závodů":
        "Races",
    "Nahrát běhy":
        "Upload runs",
    "Rychlostní model":
        "Speed model",
    "Úlohy":
        "Jobs",
    "Profil":
        "Profile",
    "Přihlášení":
        "Log in",
    "Nový účet":
        "New account",
    "O aplikaci":
        "About",
    "Závodní centrum":
        "Race centre",
    "klubový web":
        "club website",
    "Moje výsledky":
        "My results",
    "Moje vizitka":
        "My profile card",
    "Ukončit aplikaci":
        "Quit the app",
    "Odhlásit":
        "Log out",
    "Jazyk":
        "Language",
    "Kudy jsem měl běžet":
        "Where I Should Have Run",
    "rozbor postupů":
        "route analysis",
    "Nabídka":
        "Menu",
    "Světlý nebo tmavý režim":
        "Light or dark mode",
    "na tomhle počítači":
        "on this computer",
    "nepřihlášen":
        "not logged in",
    "Hlavní nabídka":
        "Main menu",
    "Analýza orientačního běhu":
        "Orienteering analysis",
    "Lokální režim · data v zařízení":
        "Local mode · data on this device",
    "Rozbor postupů počítají skripty z tvé stopy, mapy a oficiálních časů; žádná umělá inteligence.":
        "The route analysis is computed by scripts from your track, the map and the official times; no artificial intelligence.",
    "Časy a mezičasy: <a href=\"https://oris.ceskyorientak.cz/\">ORIS</a>.":
        "Times and splits: <a href=\"https://oris.ceskyorientak.cz/\">ORIS</a>.",
    "Výškopis: Mapzen Terrain Tiles (AWS)":
        "Elevation: Mapzen Terrain Tiles (AWS)",
    ", DMR 5G © ČÚZK (CC BY 4.0)":
        ", DMR 5G © ČÚZK (CC BY 4.0)",
    "Překážky: © přispěvatelé <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> (ODbL).":
        "Obstacles: © <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors (ODbL).",
    "Spodní nabídka":
        "Bottom menu",
    "Závody":
        "Races",
    "Nahrát":
        "Upload",
    "Model":
        "Model",
    "Zapomenuté heslo":
        "Forgotten password",
    "Aplikace nemá e-mail, takže kód k novému heslu ti dá správce aplikace. Platí 24 hodin a jde použít jednou.":
        "The app has no e-mail, so the code for a new password is given to you by the administrator of the app. It is valid for 24 hours and can be used once.",
    "Registrační číslo ORIS":
        "ORIS registration number",
    "Tři písmena oddílu a čtyři číslice, např. BFM0000.":
        "Three club letters and four digits, e.g. BFM0000.",
    "Jednorázový kód od správce":
        "One-time code from the administrator",
    "Nové heslo (aspoň 8 znaků)":
        "New password (at least 8 characters)",
    "Nové heslo znovu":
        "New password again",
    "Nastavit nové heslo":
        "Set the new password",
    "Zpět na přihlášení":
        "Back to login",
    "Ke každému závodu appka potřebuje tři věci: běh z hodinek, mapu s tratí a mapu bez tratě. Časy a mezičasy si načte z ORIS sama.":
        "For each race the app needs three things: a run from the watch, a map with course and a map without course. The times and splits it loads from ORIS itself.",
    "Běh z hodinek (Garmin)":
        "Run from the watch (Garmin)",
    "<b>Jeden závod</b> z Garmin Connect (na webu):":
        "<b>One race</b> from Garmin Connect (on the web):",
    "Otevři aktivitu a klikni na ozubené kolečko.":
        "Open the activity and click the cogwheel.",
    "Vyber <b>Exportovat soubor</b> (ne „originál“). Stáhne se zip, uvnitř je soubor .fit.":
        "Choose <b>Export File</b> (not “original”). A zip is downloaded with a .fit file inside.",
    "Zip nahraj v <a href=\"%(url)s\">Nahrát běhy</a>, nebo v Podkladech závodu. Rozbalovat ho nemusíš.":
        "Upload the zip in <a href=\"%(url)s\">Upload runs</a>, or in the source files of the race. You do not have to unpack it.",
    "Zip nahraj v Nahrát běhy, nebo v Podkladech závodu. Rozbalovat ho nemusíš.":
        "Upload the zip in Upload runs, or in the source files of the race. You do not have to unpack it.",
    "Ostatní možnosti exportu (TCX, GPX, Google Earth, CSV) nepoužívej: appka čte jen .fit.":
        "Do not use the other export options (TCX, GPX, Google Earth, CSV): the app reads only .fit.",
    "<b>Celý export</b> (všechny běhy najednou, appka z nich spočítá i tvůj model kopců):":
        "<b>The whole export</b> (all runs at once, from which the app also computes your hill model):",
    "Otevři <a href=\"https://www.garmin.com/en-US/account/datamanagement/\" target=\"_blank\" rel=\"noopener\">správu dat účtu Garmin</a>.":
        "Open the <a href=\"https://www.garmin.com/en-US/account/datamanagement/\" target=\"_blank\" rel=\"noopener\">data management of your Garmin account</a>.",
    "Klikni na <b>Export Your Data</b> a pak <b>Request Data Export</b>.":
        "Click <b>Export Your Data</b> and then <b>Request Data Export</b>.",
    "Odkaz na zip přijde e-mailem, za 48 hodin až 30 dní.":
        "The link to the zip arrives by e-mail, in 48 hours to 30 days.",
    "Celý zip nahraj v <a href=\"%(url)s\">Nahrát běhy</a>. Appka si nechá jen běhy ze závodů a zip smaže.":
        "Upload the whole zip in <a href=\"%(url)s\">Upload runs</a>. The app keeps only the runs from races and deletes the zip.",
    "Celý zip nahraj v Nahrát běhy. Appka si nechá jen běhy ze závodů a zip smaže.":
        "Upload the whole zip in Upload runs. The app keeps only the runs from races and deletes the zip.",
    "Běhy se se závody spárují samy podle dne, času startu a místa. Jiný běh jde vybrat v Podkladech závodu.":
        "Runs are matched with races on their own by the day, the start time and the place. Another run can be chosen in the source files of the race.",
    "Mapa z Livelox (KMZ)":
        "Map from Livelox (KMZ)",
    "V Livelox vyber závod a svou kategorii. Odkaz na Livelox bývá u závodu v appce.":
        "In Livelox choose the race and your class. The link to Livelox is usually with the race in the app.",
    "V zobrazení mapy klikni vpravo nahoře na <b>tři čárky</b> a vyber <b>Stáhnout mapu</b> (Download map).":
        "In the map view click the <b>three bars</b> at the top right and choose <b>Download map</b>.",
    "Stáhni dvakrát: <b>Mapa s tratí</b>, formát <b>KMZ</b>, a <b>Pouze mapa</b>, formát <b>KMZ</b>.":
        "Download twice: <b>Map with course</b>, format <b>KMZ</b>, and <b>Map only</b>, format <b>KMZ</b>.",
    "V Podkladech závodu nahraj první jako mapu s tratí a druhou jako mapu bez tratě.":
        "In the source files of the race upload the first as the map with course and the second as the map without course.",
    "Z mapy s tratí appka čte kontroly, z mapy bez tratě terén pro nejlepší postupy. Mapu bez tratě stačí, když nahraje jeden člověk z oddílu. Mapy vidí jen přihlášení členové a z appky nejdou stáhnout.":
        "From the map with course the app reads the controls, from the map without course the terrain for the best routes. It is enough if one person from the club uploads the map without course. Maps are visible only to logged-in members and cannot be downloaded from the app.",
    "Když Livelox stažení nedovolí":
        "When Livelox does not allow the download",
    "Pořadatel může stahování map vypnout. Pak máš dvě cesty:":
        "The organiser can switch map downloads off. Then you have two ways:",
    "<b>Nejlíp fotka papírové mapy.</b> Vyfoť celou mapu shora, za světla a bez blesku. Mapu polož rovně a nic ať nezakrývá kontroly. Nahraj ji v Podkladech jako fotku mapy. Na místo se usadí sama podle kontrol a tvé stopy (potřebuje běh z hodinek a mezičasy z ORIS); když se neusadí, jde usadit ručně.":
        "<b>Best a photo of the paper map.</b> Photograph the whole map from above, in daylight and without flash. Lay the map flat and let nothing cover the controls. Upload it in Source files as a photo of the map. It places itself by the controls and your track (it needs the run from the watch and the splits from ORIS); if it does not place itself, it can be placed by hand.",
    "<b>Jinak dva snímky obrazovky z Livelox</b> (níže). Jen pro vlastní rozbor: nesdílej je dál, pořadatel stažení vypnul záměrně.":
        "<b>Otherwise two screenshots from Livelox</b> (below). For your own analysis only: do not share them, the organiser switched the download off on purpose.",
    "Dva snímky z Livelox (Chrome na počítači)":
        "Two screenshots from Livelox (Chrome on a computer)",
    "Stiskni <b>F12</b> a pak <b>Ctrl+Shift+M</b> (zobrazení zařízení). Nahoře u Dimensions zvol <b>Responsive</b> a nastav <b>5000 × 4000</b>.":
        "Press <b>F12</b> and then <b>Ctrl+Shift+M</b> (device toolbar). At the top next to Dimensions choose <b>Responsive</b> and set <b>5000 × 4000</b>.",
    "V Livelox zavři křížkem postranní panel se závodníky. Mapu přibliž co nejvíc tak, aby byla celá vidět.":
        "In Livelox close the side panel with the competitors with the cross. Zoom the map in as much as possible so that the whole map is still visible.",
    "Tři tečky úplně vpravo v liště s Dimensions → <b>Capture full size screenshot</b>. Snímek se uloží do Stažených. To je <b>snímek s tratí</b>.":
        "Three dots at the far right of the Dimensions bar → <b>Capture full size screenshot</b>. The screenshot is saved to Downloads. This is the <b>screenshot with the course</b>.",
    "<b>Mapu neposouvej ani nepřibližuj.</b> V Livelox vpravo dole klikni na malý výstupek, vysune se panel nastavení. Druhý posuvník dej úplně doleva, tím zmizí kontroly a trať. Panel zavři křížkem vpravo nahoře, těsně pod ozubeným kolečkem.":
        "<b>Do not move or zoom the map.</b> In Livelox click the small tab at the bottom right, the settings panel slides out. Move the second slider all the way to the left, which makes the controls and the course disappear. Close the panel with the cross at the top right, just below the cogwheel.",
    "Znovu tři tečky → <b>Capture full size screenshot</b>. To je <b>snímek bez tratě</b>.":
        "Three dots again → <b>Capture full size screenshot</b>. This is the <b>screenshot without the course</b>.",
    "Oba snímky nahraj do polí „Snímek z Livelox s tratí“ a „Snímek z Livelox bez tratě“ v Podkladech závodu.":
        "Upload both screenshots to the fields “Livelox screenshot with course” and “Livelox screenshot without course” in the source files of the race.",
    "Proč neposouvat: appka usadí jen snímek s tratí (podle kontrol a tvé stopy) a snímku bez tratě dá stejné místo. Snese posun o pár pixelů, ne jiné přiblížení nebo jinou velikost okna.":
        "Why not to move: the app places only the screenshot with the course (by the controls and your track) and gives the screenshot without the course the same place. It tolerates a shift of a few pixels, not a different zoom or a different window size.",
    "Když pořadatel nahrál mapu s kontrolami natvrdo, trať vypnout nejde. Pak zbývá fotka mapy. Snímek s tratí jde nahrát i tak, nejlepší postupy z něj ale nebudou.":
        "When the organiser uploaded a map with the controls burned in, the course cannot be switched off. Then a photo of the map remains. The screenshot with the course can be uploaded anyway, but there will be no best routes from it.",
    "Poznámky u úseku":
        "Notes on a leg",
    "Na stránce závodu klikni na úsek. Pod mapou je, co se na úseku stalo. Poznámky mění, jak appka čte ztrátu a z kterých úseků se učí tvůj model rychlosti.":
        "On the page of the race click a leg. Below the map is what happened on the leg. The notes change how the app reads the loss and which legs your speed model learns from.",
    "Záměrná zastávka":
        "Deliberate stop",
    "Zastavení se nepočítá jako chyba (pití, tkanička, pomoc jinému). U občerstvení to appka pozná sama.":
        "A stop does not count as a mistake (a drink, a shoelace, helping someone). At a refreshment control the app recognises it itself.",
    "Ztráta kontaktu s mapou":
        "Lost contact with the map",
    "Celá ztráta úseku je chyba, ne volba postupu. Z úseku se model neučí.":
        "The whole loss of the leg is a mistake, not a route choice. The model does not learn from the leg.",
    "Zelená":
        "Green",
    "„Proběhl jsem ji“ nebo „obíhal jsem ji“. Když jsi ji obíhal, body stopy, které GPS dala do zelené, se do modelu nepočítají.":
        "“I ran through it” or “I ran around it”. If you ran around it, the track points that the GPS put into the green are not counted in the model.",
    "Únava":
        "Fatigue",
    "1 až 3 jen popisuje. Od 4 se úsek vyřadí z modelu a ztráta provedením se vede jako únava.":
        "1 to 3 only describes. From 4 the leg is left out of the model and the loss by execution is counted as fatigue.",
    "Poznámka":
        "Note",
    "Volný text pro tebe.":
        "Free text for you.",
    "Plánovaný postup":
        "Planned route",
    "Nakresli, kudy jsi chtěl běžet. Appka ho ocení tvým modelem a porovná s nejlepším postupem.":
        "Draw where you wanted to run. The app prices it with your model and compares it with the best route.",
    "Opravit moji stopu":
        "Correct my track",
    "Když GPS na úseku zlobí (město, vysoké domy; appka napíše „GPS tu asi zlobí“), nakresli, kudy jsi opravdu běžel. Čára nahradí stopu úseku, úsek se z modelu vyřadí. Tlačítko Vrátit GPS stopu ji vrátí.":
        "When the GPS misbehaves on a leg (city, tall buildings; the app writes “The GPS is probably misbehaving here”), draw where you really ran. The line replaces the track of the leg, and the leg is left out of the model. The button Restore the GPS track brings it back.",
    "Leží celá mapa vedle stopy (všechny kontroly posunuté stejně)? V Podkladech je „Usadit mapu ručně podle kontrol“. Jde vrátit.":
        "Is the whole map lying beside the track (all controls shifted the same way)? In Source files there is “Place the map by hand by the controls”. It can be undone.",
    "Další věty u úseku píše appka sama:":
        "The app writes other sentences about a leg on its own:",
    "Nejlepší postup":
        "Best route",
    "Modrá čára: nejrychlejší postup pro tebe podle tvého modelu rychlosti.":
        "Blue line: the fastest route for you by your speed model.",
    "Průměrný běžec":
        "Average runner",
    "Šedá tečkovaná čára: kudy by běžel běžec s učebnicovým modelem a tvou rychlostí po cestě. Věta řekne, proč je pro tebe lepší jiný postup.":
        "Grey dotted line: where a runner with a textbook model and your speed on paths would run. The sentence tells why a different route is better for you.",
    "Kdyby ses ztratil":
        "If you got lost",
    "Co je kolem kontroly: čeho se chytit, náběhový bod a zarážka za kontrolou.":
        "What is around the control: what to catch onto, the attack point and the catching feature beyond the control.",
    "Ztratil jsem se u kontroly":
        "I got lost at a control",
    "<b>Rozbor po závodě</b> pro chvíli „byl jsem u kontroly, neviděl jsem ji a nevěděl jsem přesně, kde jsem“: co tam bylo vidět a jak ses měl vrátit. Na závodě se mobil ani jiné pomůcky používat nesmějí, stránka je na doma. Otevřeš ji tlačítkem <b>Ztratil jsem se u kontroly</b> na stránce závodu (nebo u úseku v části Kdyby ses ztratil). Potřebuje mapu s tratí a mapu bez tratě; s během (.fit) ukáže i místa ze stopy.":
        "<b>An analysis after the race</b> for the moment “I was at the control, I did not see it and I did not know exactly where I was”: what was visible there and how you should have got back. A phone or other aids must not be used in a race, the page is for home. You open it with the button <b>I got lost at a control</b> on the page of the race (or at a leg in the section If you got lost). It needs the map with course and the map without course; with a run (.fit) it also shows the places from the track.",
    "Poprvé se mapa kolem kontrol asi minutu připravuje.":
        "The first time the map around the controls takes about a minute to prepare.",
    "Nahoře vyber kontrolu.":
        "Choose a control at the top.",
    "S během: <b>Po závodě: kde jsem se ztratil</b> ukáže místa u kontroly, kde ses podle stopy zdržel.":
        "With a run: <b>After the race: where I got lost</b> shows the places at the control where you lingered according to the track.",
    "Bez běhu, nebo když stopa místo nechytila: <b>Kde jsem asi byl</b>. Ťukni do mapy, kde jsi asi byl, a vyber, o kolik si nejsi jistý (25, 50, 100 nebo 150 m; v lese je výchozí 50 m, na sprintu 25 m). Oranžový kruh je místo, kde jsi mohl být.":
        "Without a run, or when the track did not catch the place: <b>Where I probably was</b>. Tap the map where you probably were and choose how unsure you are (25, 50, 100 or 150 m; in the forest the default is 50 m, in a sprint 25 m). The orange circle is where you could have been.",
    "Appka napíše jednu až tři věty: kam jsi měl jít, podél čeho, kde byla kontrola. Modrá čára ukazuje cestu, čísla jsou záchytné body.":
        "The app writes one to three sentences: where you should have gone, along what, where the control was. The blue line shows the way, the numbers are relocating features.",
    "Nedalo se minout":
        "Could not be missed",
    "Dlouhá věc (cesta, vodoteč, plot, okraj zástavby nebo velké paseky), na kterou bys narazil odkudkoli z kruhu, kdybys šel daným směrem. Appka vybere nejjistější, ne nejbližší.":
        "A long feature (a path, a stream, a fence, the edge of a built-up area or a large clearing) that you would hit from anywhere in the circle if you went in the given direction. The app picks the surest, not the nearest.",
    "Neměl jsi hádat směr ke kontrole":
        "You should not have guessed the direction to the control",
    "Když byla jistá věc dál, než je kruh nejistoty, appka radí, že jsi měl dojít (nebo se vrátit) nejdřív k ní a teprve odtud ke kontrole.":
        "When the sure feature was further than the circle of uncertainty, the app advises that you should have gone (or gone back) to it first and only from there to the control.",
    "Jen kontrola a okolí":
        "Only the control and its surroundings",
    "Když vůbec nevíš, kde jsi byl: co bylo kolem kontroly nejjistější.":
        "When you do not know at all where you were: what was surest around the control.",
    "Po závodě: kde jsem se ztratil":
        "After the race: where I got lost",
    "Místa do 100 m od kontroly, kde jsi podle stopy zpomalil, kroužil nebo se otočil. U každého, co jsi měl vidět a kudy se vrátit.":
        "Places within 100 m of the control where, according to the track, you slowed down, circled or turned. For each, what you should have seen and how to get back.",
    "Popis kontroly":
        "Control description",
    "Nepovinný, napíšeš ho ručně (třeba „kupka, severní úpatí“). Ukáže se v radě, nic se z něj nepočítá.":
        "Optional, you write it by hand (e.g. “knoll, north foot”). It appears in the advice, nothing is computed from it.",
    "Rada je odhad z kresby mapy, bez vrstevnic a skal. Do oplocených a zakázaných míst nevede.":
        "The advice is an estimate from the drawing of the map, without contours and cliffs. It does not lead into fenced and out-of-bounds places.",
    "Úlohy na pozadí":
        "Background jobs",
    "Načítání z ORIS, zpracování nahraných souborů, analýzy a přepočty modelu běží na pozadí. Stránka se sama obnoví, až doběhnou.":
        "Loading from ORIS, processing of uploaded files, analyses and recomputing of the model run in the background. The page refreshes itself when they finish.",
    "Zastavit všechny moje":
        "Stop all of mine",
    "Čekající se zruší hned. Běžící se zastaví do pár sekund; co bylo hotové, zůstane, rozpracovaný závod se zahodí a platí jeho předchozí rozbor.":
        "Waiting ones are cancelled at once. Running ones stop within a few seconds; what was finished stays, the race being computed is discarded and its previous analysis applies.",
    "Zadáno":
        "Submitted",
    "Úloha":
        "Job",
    "Stav":
        "Status",
    "Výsledek":
        "Result",
    "zastavuje se":
        "stopping",
    "Zastavit":
        "Stop",
    "Podrobnosti":
        "Details",
    "Usadit fotku ručně":
        "Place the photo by hand",
    "Zkusit znovu":
        "Try again",
    "Oříznout snímek":
        "Crop the screenshot",
    "Zatím žádné úlohy.":
        "No jobs yet.",
    "Rozbor tvých závodů: stopa z hodinek na mapě, nejlepší postupy, mezičasy kategorie.":
        "Analysis of your races: the track from the watch on the map, best routes, splits of the class.",
    "Registrační číslo nebo uživatelské jméno":
        "Registration number or user name",
    "Heslo":
        "Password",
    "Přihlásit":
        "Log in",
    "Ještě nemáš účet? <a href=\"%(url)s\">Založit účet</a> (registrační číslo ORIS a kód od správce).":
        "Do not have an account yet? <a href=\"%(url)s\">Create an account</a> (ORIS registration number and a code from the administrator).",
    "<a href=\"%(url)s\">Zapomenuté heslo</a>: nové si nastavíš s jednorázovým kódem, který ti dá správce aplikace.":
        "<a href=\"%(url)s\">Forgotten password</a>: you set a new one with a one-time code given to you by the administrator of the app.",
    "Rozbory člena":
        "Analyses of a member",
    "Rozbory postupů vidí jen ten, komu patří. Stopy z hodinek ostatních členů se v aplikaci neukazují.":
        "Route analyses are seen only by the one they belong to. The tracks from the watches of other members are not shown in the app.",
    "Moje závody":
        "My races",
    "Vizitka na klubovém webu":
        "Profile card on the club website",
    "Můj model rychlosti":
        "My speed model",
    "Profil rychlostního modelu":
        "Profile of the speed model",
    "Model se spočítá sám po první analýze závodu, ke kterému je mapa s tratí, mapa bez tratě a běh z hodinek.":
        "The model is computed on its own after the first analysis of a race that has a map with course, a map without course and a run from the watch.",
    "Podle něj se počítají nejlepší postupy. Model se učí z tvých stop ve všech závodech. Nový závod nebo poznámka ho změní; postupy ostatních závodů se přepočítají tlačítkem Přepočítat všechno.":
        "The best routes are computed by it. The model learns from your tracks in all races. A new race or a note changes it; the routes of the other races are recomputed with the button Recompute everything.",
    "Terén":
        "Terrain",
    "závod":
        "race",
    "závody":
        "races",
    "závodů":
        "races",
    "Kopce":
        "Hills",
    "%(n)s běhů z Garminu":
        "%(n)s runs from Garmin",
    "výchozí tvar (bez exportu z Garminu)":
        "default shape (without a Garmin export)",
    "Vliv stoupání":
        "Effect of climbing",
    "1 m nahoru = <b class=\"ob-cislo\">%(k)s</b> m po rovině":
        "1 m up = <b class=\"ob-cislo\">%(k)s</b> m on the flat",
    "Moje rychlost po rovině (km/h)":
        "My speed on the flat (km/h)",
    "málo dat, převážně odhad":
        "little data, mostly an estimate",
    "Rychlost na rovné cestě":
        "Speed on a flat path",
    "Z čeho":
        "Based on",
    "čisté úseky (bez chyb) z %(races)s závodů; novější mají vyšší váhu (poločas %(days)s dní)":
        "clean legs (without mistakes) from %(races)s races; newer ones weigh more (half-life %(days)s days)",
    "Spočítáno":
        "Computed",
    "Přepočítat teď":
        "Recompute now",
    "Proti průměrnému běžci":
        "Against the average runner",
    "Na <b>%(yours)s</b> z %(legs)s úseků (%(pct)s %%, %(races)s %(race_word)s) je tvůj nejlepší postup jiný a rychlejší než postup běžce s průměrným modelem.":
        "On <b>%(yours)s</b> of %(legs)s legs (%(pct)s %%, %(races)s %(race_word)s) your best route is different and faster than the route of a runner with the average model.",
    "Na dalších %(n)s by průměrný běžec běžel jinudy, ale tobě by to trvalo skoro stejně.":
        "On another %(n)s the average runner would run another way, but it would take you about the same.",
    "Nejčastěji proto, že":
        "Most often because",
    "%(event)s, úsek %(leg)s":
        "%(event)s, leg %(leg)s",
    "o %(gain)s rychlejší":
        "%(gain)s faster",
    "Průměrný běžec tu je model z učebnice: sklon podle učebnicového pravidla, terény podle normy ISOM a tvoje rychlost po rovné cestě. Porovnává se tedy tvar tvého modelu, ne kondice.":
        "The average runner here is a textbook model: the slope by the textbook rule, the terrain by the ISOM standard and your speed on a flat path. So the shape of your model is compared, not fitness.",
    "Bez tvého exportu z Garminu nemáš vlastní model kopců, proto se porovnávají jen terény.":
        "Without your Garmin export you have no hill model of your own, so only the terrain is compared.",
    "Spočítá se po přepočtu nejlepších postupů (u závodu „Přepočítat postupy“).":
        "Computed after the best routes are recomputed (at the race “Recompute routes”).",
    "Terény":
        "Terrain",
    "vůči cestě":
        "against path",
    "kolik dat (s)":
        "how much data (s)",
    "data říkají":
        "data say",
    "výchozí (ISOM)":
        "default (ISOM)",
    "nejistota":
        "uncertainty",
    "spolehlivost":
        "reliability",
    "dobrá":
        "good",
    "střední":
        "medium",
    "malá":
        "low",
    "Rychlosti platí na rovině. „Výchozí“ je hodnota podle mapového klíče ISOM; čím víc sekund v terénu máš, tím víc se použitá hodnota posune k tomu, co říkají tvoje data. Nejistota je odhad jedné směrodatné odchylky: vychází z rozptylu tvých rychlostí v terénu a z toho, kolik nezávislých měření to je (15 s běhu = jedno); terén bez dat má nejistotu výchozí hodnoty (asi 25 %%).":
        "Speeds apply on the flat. “Default” is the value by the ISOM map key; the more seconds in the terrain you have, the more the value used moves towards what your data say. The uncertainty is an estimate of one standard deviation: it comes from the spread of your speeds in the terrain and from how many independent measurements that is (15 s of running = one); a terrain without data has the uncertainty of the default value (about 25 %%).",
    "Čára je model, tečky jsou naměřené hodnoty z běhů po 30 s. Nad čárkovanou jedničkou je to pomalejší než po rovině. 1 m stoupání stojí jako %(k)s m běhu po rovině.":
        "The line is the model, the dots are values measured from runs in 30 s stretches. Above the dashed one it is slower than on the flat. 1 m of climbing costs as much as %(k)s m of running on the flat.",
    "Tvar kopců je spočítaný z tvých běhů v Garmin exportu (%(n)s běhů).":
        "The shape of the hills is computed from your runs in the Garmin export (%(n)s runs).",
    "Tvar kopců je zatím výchozí (z běhů autora aplikace). Vlastní se spočítá, když nahraješ celý export z Garminu.":
        "The shape of the hills is the default for now (from the runs of the author of the app). Your own is computed when you upload a whole export from Garmin.",
    "Sklon":
        "Slope",
    "čas ×":
        "time ×",
    "cesta km/h":
        "path km/h",
    "cesta min/km":
        "path min/km",
    "les km/h":
        "forest km/h",
    "Závody v modelu":
        "Races in the model",
    "Závod":
        "Race",
    "Datum":
        "Date",
    "Váha":
        "Weight",
    "Čisté sekundy":
        "Clean seconds",
    "předpověď z ostatních závodů":
        "prediction from the other races",
    "chyba po úsecích":
        "error by legs",
    "„Předpověď z ostatních závodů“ je zkouška modelu: závod se vynechá, model se spočítá ze zbylých a jeho čas na čistých úsecích vynechaného závodu se porovná se skutečným. Kladné číslo znamená, že model čekal delší čas.":
        "“Prediction from the other races” is a test of the model: a race is left out, the model is computed from the rest and its time on the clean legs of the left-out race is compared with the real one. A positive number means the model expected a longer time.",
    "Jak dobře model sedí":
        "How well the model fits",
    "Kontrola modelu, ne rada pro běh: řadí model úseky závodu stejně jako kategorie? Porovnává se čas nejlepšího postupu podle tvého modelu s referenčním časem kategorie (průměr nejrychlejší čtvrtiny běžců na úseku). Nemá sedět čas (ostatní běhají jinak rychle), ale pořadí a poměry úseků. Úsek, kde se model od kategorie liší o čtvrtinu a víc, ukazuje, kde mapa nebo model nesedí (špatně přečtený terén, zakázaný průchod, těžká dohledávka).":
        "A check of the model, not advice for running: does the model order the legs of the race the same way as the class? The time of the best route by your model is compared with the reference time of the class (the average of the fastest quarter of runners on the leg). It is not the time that should fit (the others run at different speeds) but the order and the proportions of the legs. A leg where the model differs from the class by a quarter or more shows where the map or the model does not fit (a wrongly read terrain, an out-of-bounds passage, a hard search for the control).",
    "Pořadová korelace":
        "Rank correlation",
    "Co to říká":
        "What it says",
    "Úseky, kde se liší":
        "Legs where it differs",
    "%(n)s úseků":
        "%(n)s legs",
    "<b>%(name)s</b> model %(model)s, reference %(ref)s (%(pct)s %%): %(text)s":
        "<b>%(name)s</b> model %(model)s, reference %(ref)s (%(pct)s %%): %(text)s",
    "žádné":
        "none",
    "Historie modelu":
        "History of the model",
    "Závodů":
        "Races",
    "Rovná cesta km/h":
        "Flat path km/h",
    "Usadit mapu ručně":
        "Place the map by hand",
    "kategorie %(name)s":
        "class %(name)s",
    "Jen když je <b>celá mapa</b> posunutá (všechny kontroly vedle tvé stopy stejným směrem). Když zlobí GPS jen na pár úsecích (město, vysoké domy), oprav si raději stopu u úseku („Opravit moji stopu“).":
        "Only when the <b>whole map</b> is shifted (all controls beside your track in the same direction). When the GPS misbehaves only on a few legs (city, tall buildings), rather correct the track at the leg (“Correct my track”).",
    "Vyber kontrolu v seznamu a klikni na mapě na střed jejího kolečka. <b>Klikni aspoň na %(min_points)s kontroly, co nejdál od sebe.</b> Kde kontroly leží v terénu, ví aplikace z tvé stopy v oficiálních časech ražení. Uložením se posune %(moved)s a analýzy závodu se pustí znovu; vrátit to jde v Podkladech.":
        "Choose a control in the list and click the map at the centre of its circle. <b>Click at least %(min_points)s controls, as far from each other as possible.</b> Where the controls lie in the terrain, the app knows from your track at the official punch times. Saving moves %(moved)s and the analyses of the race run again; it can be undone in Source files.",
    "mapa s tratí i mapa bez tratě z tvých snímků":
        "the map with course and the map without course from your screenshots",
    "mapa celého závodu (s tratí všech kategorií i bez tratě)":
        "the map of the whole race (with the course of all classes and without course)",
    "Pro tuhle kategorii už je mapa z KMZ, která je přesnější. Fotka se nepoužije.":
        "This class already has a map from a KMZ, which is more accurate. The photo will not be used.",
    "Vyber kontrolu v seznamu a klikni na fotce na střed jejího kolečka (start: střed trojúhelníku, cíl: střed dvojkolečka). <b>Klikni aspoň na %(min_points)s kontroly, co nejdál od sebe (rohy tratě). Víc bodů = přesnější.</b> Kde kontroly leží v terénu, ví aplikace z tvé stopy v oficiálních časech ražení.":
        "Choose a control in the list and click the photo at the centre of its circle (start: the centre of the triangle, finish: the centre of the double circle). <b>Click at least %(min_points)s controls, as far from each other as possible (the corners of the course). More points = more accurate.</b> Where the controls lie in the terrain, the app knows from your track at the official punch times.",
    "Fotka mapy; klepnutím označíš vybranou kontrolu":
        "Photo of the map; a tap marks the selected control",
    "Kontroly":
        "Controls",
    "Ukázat moji stopu přes mapu":
        "Show my track over the map",
    "Ukázat moji stopu přes fotku":
        "Show my track over the photo",
    "Uložit":
        "Save",
    "Zpět":
        "Back",
    "Uložením se fotka narovná a stane se mapou s tratí kategorie; analýza všech jejích běžců se pustí znovu. Body si stránka pamatuje, můžeš se k nim vrátit.":
        "On saving, the photo is straightened and becomes the map with course of the class; the analysis of all its runners runs again. The page remembers the points, you can come back to them.",
    "Registrační číslo ORIS (nepovinné, např. BFM0000)":
        "ORIS registration number (optional, e.g. BFM0000)",
    "Podle něj se z ORIS načtou tvoje závody a kategorie. Zadat ho jde jen jednou.":
        "Your races and classes are loaded from ORIS by it. It can be entered only once.",
    "Přihlašovací jméno":
        "Login name",
    "účet ho nemá":
        "the account has none",
    "zatím nenačteno":
        "not loaded yet",
    "Závody z ORIS načteny":
        "Races loaded from ORIS",
    "zatím ne":
        "not yet",
    "Podle registračního čísla se z ORIS načítají tvoje závody, kategorie, Livelox ID a oficiální mezičasy. Účet k němu patří napořád, změnit ho nejde.":
        "Your races, classes, Livelox ID and official splits are loaded from ORIS by the registration number. The account belongs to it for good, it cannot be changed.",
    "Moje výsledky v archivu":
        "My results in the archive",
    "Změna hesla":
        "Change of password",
    "Současné heslo":
        "Current password",
    "Změnit heslo":
        "Change password",
    "Zrušení účtu":
        "Closing the account",
    "Zrušení smaže účet a všechno, co patří jen tobě: závody v aplikaci (%(races)s), běhy z hodinek (%(activities)s), rozbory (%(analyses)s), poznámky a plánované postupy (%(notes)s), osobní modely (%(models)s) a závody, které jsi přidal ručně a nikdo jiný je nemá. Nejde to vrátit.":
        "Closing deletes the account and everything that belongs only to you: races in the app (%(races)s), runs from the watch (%(activities)s), analyses (%(analyses)s), notes and planned routes (%(notes)s), personal models (%(models)s) and races you added by hand that nobody else has. It cannot be undone.",
    "Zůstane, co je sdílené pro závod: mapa bez tratě, mapa s tratí kategorie, zakázané čáry a občerstvovačky (jen už u nich nebude tvoje jméno). Účet si můžeš později založit znovu.":
        "What is shared for a race stays: the map without course, the map with course of the class, impassable lines and refreshment controls (only your name will no longer be on them). You can create the account again later.",
    "Heslo pro potvrzení":
        "Password to confirm",
    "Zrušit účet a smazat moje data":
        "Close the account and delete my data",
    "Soukromí":
        "Privacy",
    "Aplikace běží jen na tomhle počítači. Mapy, běhy z hodinek, poznámky a modely jsou ve složce <code>%(data_dir)s</code> a nikam se neposílají. Ven jdou jen dotazy na ORIS (závody, mezičasy) a na výškopis a OpenStreetMap (jen výřez mapy, ne tvoje stopa). Zálohu uděláš zkopírováním té složky.":
        "The app runs only on this computer. Maps, runs from the watch, notes and models are in the folder <code>%(data_dir)s</code> and are sent nowhere. Only requests to ORIS (races, splits) and for the elevation and OpenStreetMap (just a cut-out of the map, not your track) go out. You make a backup by copying that folder.",
    "Tvoje stopy z hodinek a poznámky vidíš jen ty. Mapa bez tratě, občerstvovačky a zakázané přechody jsou sdílené pro závod, takže poslouží i ostatním přihlášeným členům, kteří ho běželi. Celý export z Garminu se po zpracování z aplikace maže; zůstanou jen běhy spárované se závody a z ostatních jen odvozený model kopců.":
        "Only you see your tracks from the watch and your notes. The map without course, refreshment controls and impassable crossings are shared for the race, so they also serve the other logged-in members who ran it. The whole Garmin export is deleted from the app after processing; only the runs matched with races stay, and from the others only the derived hill model.",
    "Aplikace ukončena":
        "App closed",
    "Aplikace je ukončená":
        "The app is closed",
    "Tohle okno můžeš zavřít. Data zůstávají ve složce <code>%(data_dir)s</code>, příště je aplikace najde zase.":
        "You can close this window. The data stays in the folder <code>%(data_dir)s</code>, the app will find it again next time.",
    "%(m)s m stoupání":
        "%(m)s m of climb",
    "%(n)s kontrol":
        "%(n)s controls",
    "oficiální čas":
        "official time",
    "moje závody":
        "my races",
    "Rozbor „Ztratil jsem se u kontroly“ bude po závodě.":
        "The analysis “I got lost at a control” will be available after the race.",
    "Závod v ORIS":
        "Race in ORIS",
    "Výsledky (ORIS)":
        "Results (ORIS)",
    "Výsledky (OResults)":
        "Results (OResults)",
    "Klubový web":
        "Club website",
    "Běžel jsem jinou kategorii":
        "I ran another class",
    "Kategorie":
        "Class",
    "Změnit kategorii":
        "Change the class",
    "Načíst kategorie závodu z ORIS":
        "Load the classes of the race from ORIS",
    "Oficiální čas a mezičasy se vezmou z výsledků zvolené kategorie (z ORIS jednou) a rozbor se spočítá znovu s její tratí. Rozbor a poznámky k úsekům dosavadní kategorie se smažou, trať je jiná.":
        "The official time and splits are taken from the results of the chosen class (from ORIS once) and the analysis is computed again with its course. The analysis and the notes on the legs of the previous class are deleted, the course is different.",
    "Kategorii jsi vybral sám; synchronizace s ORIS ji nezmění.":
        "You chose the class yourself; the synchronisation with ORIS will not change it.",
    "Poslední analýza selhala.":
        "The last analysis failed.",
    "Poslední analýzu jsi zastavil.":
        "You stopped the last analysis.",
    "Platí rozbor, který byl hotový před ní.":
        "The analysis that was finished before it applies.",
    "Spustit znovu":
        "Run again",
    "Co závod potřebuje k rozboru":
        "What the race needs for the analysis",
    "běh z hodinek (.fit)":
        "run from the watch (.fit)",
    "stopa na mapě":
        "track on the map",
    "mapa s tratí":
        "map with course",
    "kontroly a jejich pořadí":
        "controls and their order",
    "mapa bez tratě":
        "map without course",
    "nejlepší postupy":
        "best routes",
    "Doplnit":
        "Add",
    "Části stránky":
        "Parts of the page",
    "Mapa a úseky":
        "Map and legs",
    "Podklady":
        "Source files",
    "Nastavení závodu":
        "Race settings",
    "Jak je rozbor spočítaný (časy, výškopis, zakázané přechody)":
        "How the analysis is computed (times, elevation, impassable crossings)",
    "Čas start–cíl <b>%(total)s</b>.":
        "Start–finish time <b>%(total)s</b>.",
    "Časy na kontrolách jsou oficiální mezičasy z ORIS":
        "The times at the controls are the official splits from ORIS",
    "hodinky a časomíra se liší o %(s)s s":
        "the watch and the timing differ by %(s)s s",
    "Časy na kontrolách jsou odhad z GPS; oficiální mezičasy nešly použít (%(reason)s).":
        "The times at the controls are an estimate from the GPS; the official splits could not be used (%(reason)s).",
    "Časy na kontrolách jsou odhad z GPS (závod nemá mezičasy v ORIS).":
        "The times at the controls are an estimate from the GPS (the race has no splits in ORIS).",
    "<b>Nejlepší postupy se právě počítají</b>; stopa, mezičasy a typy chyb jsou už hotové.":
        "<b>The best routes are being computed right now</b>; the track, splits and kinds of mistakes are already done.",
    "<b>Nejlepší postupy nejsou spočítané</b>; analýzu jde spustit znovu v Podkladech.":
        "<b>The best routes are not computed</b>; the analysis can be run again in Source files.",
    "<b>Nejlepší postupy z fotky nepočítáme</b>, terén se z ní nedá spolehlivě přečíst. Až pořadatel zveřejní mapu na Livelox, nahraj KMZ a přepočítá se to.":
        "<b>We do not compute best routes from a photo</b>, the terrain cannot be read reliably from it. When the organiser publishes the map on Livelox, upload the KMZ and it will be recomputed.",
    "<b>Nejlepší postupy chybí</b>, dokud někdo nenahraje mapu bez tratě.":
        "<b>The best routes are missing</b> until somebody uploads the map without course.",
    "Výškopis: %(dem)s.":
        "Elevation: %(dem)s.",
    "DMR 5G (ČÚZK, laserové skenování)":
        "DMR 5G (ČÚZK, laser scanning)",
    "AWS Terrain Tiles (zdroj kolem 30 m)":
        "AWS Terrain Tiles (source around 30 m)",
    "Zakázané přechody: %(forbidden)s zakázaných a %(hard)s těžko překonatelných čar, %(crossings)s průchodů":
        "Impassable crossings: %(forbidden)s impassable and %(hard)s hardly passable lines, %(crossings)s crossings",
    "%(areas)s zakázaných prostorů ze šrafování mapy":
        "%(areas)s out-of-bounds areas from the hatching of the map",
    "Postupy jsou spočítané se starším modelem rychlosti. Přepočítat všechno je přepočítá u všech závodů s jedním modelem.":
        "The routes are computed with an older speed model. Recompute everything recomputes them for all races with one model.",
    "Jen tenhle závod":
        "Only this race",
    "Nejlepší postupy jsou ze starší verze výpočtu (nová u každého úseku ukáže, kudy by běžel průměrný běžec a proč je pro tebe lepší jiný postup, na sprintových mapách nevede postupy domy ani přes zdi a tvoji stopu vedle cesty oceňuje jako cestu). Přepočet trvá pár minut a spočítá znovu i záchytné body.":
        "The best routes are from an older version of the computation (the new one shows for each leg where the average runner would run and why a different route is better for you, on sprint maps it leads routes neither through houses nor across walls, and it prices your track beside a path as a path). The recomputation takes a few minutes and also recomputes the relocating features.",
    "Přepočítat postupy":
        "Recompute routes",
    "Záchytné a náběhové body u kontrol jsou ze starší verze výpočtu. Přepočet trvá do minuty a postupy nemění.":
        "The relocating features and attack points of the controls are from an older version of the computation. The recomputation takes up to a minute and does not change the routes.",
    "Záchytné a náběhové body u kontrol tenhle rozbor ještě nemá. Přepočet trvá do minuty a postupy nemění.":
        "This analysis does not have the relocating features and attack points of the controls yet. The recomputation takes up to a minute and does not change the routes.",
    "Přepočítat záchytné body":
        "Recompute relocating features",
    "Předchozí úsek":
        "Previous leg",
    "Předchozí úsek (←)":
        "Previous leg (←)",
    "Úseky":
        "Legs",
    "Další úsek":
        "Next leg",
    "Další úsek (→)":
        "Next leg (→)",
    "obrázku":
        "an image",
    "snímku Livelox":
        "a Livelox screenshot",
    "fotky":
        "a photo",
    "Mapa z %(src)s, přesnost asi ±%(acc)s m":
        "Map from %(src)s, accuracy about ±%(acc)s m",
    "Kontroly a stopa leží na mapě s touhle přesností":
        "The controls and the track lie on the map with this accuracy",
    "záchytné a náběhové body u kontrol ber s rezervou (terén je z mapy bez tratě, poloha kontroly z fotky)":
        "treat the relocating features and attack points of the controls with caution (the terrain is from the map without course, the position of the controls from a photo)",
    "<span class=\"badge\">Mapa bez tratě ze snímku Livelox, přesnost asi ±%(acc)s m</span> Z ní je přečtený terén pro nejlepší postupy. Až bude mapa bez tratě jako KMZ, nahraj ji a postupy se přepočítají.":
        "<span class=\"badge\">Map without course from a Livelox screenshot, accuracy about ±%(acc)s m</span> The terrain for the best routes is read from it. When the map without course is available as a KMZ, upload it and the routes will be recomputed.",
    "Vrstvy mapy":
        "Map layers",
    "Mapa":
        "Map",
    "Mapa s tratí":
        "Map with course",
    "Další možnosti":
        "Other options",
    "Záchytné body":
        "Relocating features",
    "Načítám stopu a postupy…":
        "Loading the track and routes…",
    "Zpět o bod":
        "Undo a point",
    "Hotovo":
        "Done",
    "Zrušit":
        "Cancel",
    "Minuty ztráty na úseku":
        "Minutes lost on a leg",
    "Ztráta po úsecích":
        "Loss by legs",
    "Přehled úseků":
        "Overview of legs",
    "Klikni na úsek (v mapě, v grafu nebo tady) a otevře se jeho rozbor a poznámky.":
        "Click a leg (on the map, in the chart or here) and its analysis and notes open.",
    "Celá trať (Esc)":
        "Whole course (Esc)",
    "Celá trať":
        "Whole course",
    "Co se na úseku stalo":
        "What happened on the leg",
    "záměrná zastávka (nepočítá se jako chyba)":
        "deliberate stop (does not count as a mistake)",
    "ztráta kontaktu s mapou":
        "lost contact with the map",
    "neuvedeno":
        "not stated",
    "proběhl jsem ji":
        "I ran through it",
    "obíhal jsem ji":
        "I ran around it",
    "Únava 1–3 jen popisuje. Výpočet mění až 4–5: úsek se vyřadí z modelu a ztráta provedením se vede jako únava.":
        "Fatigue 1–3 only describes. Only 4–5 changes the computation: the leg is left out of the model and the loss by execution is counted as fatigue.",
    "Nakreslit plánovaný postup":
        "Draw a planned route",
    "Smazat plán":
        "Delete the plan",
    "Když GPS zlobí: nakresli, kudy jsi na úseku opravdu běžel":
        "When the GPS misbehaves: draw where you really ran on the leg",
    "Vrátit GPS stopu":
        "Restore the GPS track",
    "bez ztráty":
        "no loss",
    "do 1 min":
        "up to 1 min",
    "do 3 min":
        "up to 3 min",
    "víc":
        "more",
    "nejlepší postup":
        "best route",
    "další možnosti":
        "other options",
    "průměrný běžec":
        "average runner",
    "plánovaný postup":
        "planned route",
    "zakázaný přechod nebo prostor":
        "impassable line or out-of-bounds area",
    "zastávka":
        "stop",
    "záchytný bod":
        "relocating feature",
    "Mapa závodu je dílo pořadatele a mapaře a je chráněná autorským právem. V aplikaci slouží jen přihlášeným členům oddílu k rozboru vlastního běhu; nejde stáhnout a nesmí se šířit dál.":
        "The map of the race is the work of the organiser and the map-maker and is protected by copyright. In the app it serves only logged-in members of the club for analysing their own run; it cannot be downloaded and must not be shared further.",
    "<b>Nejlepší</b> je čas modelu pro nejrychlejší postup, <b>volba</b> je o kolik je tvůj postup pomalejší při stejném tempu, <b>provedení</b> je o kolik jsi byl pomalejší než tvoje tempo na postupu, který jsi běžel. Rozdíly do 20 s na úsek jsou v šumu modelu. ✓ ve sloupci model značí úseky, ze kterých se učí tvůj osobní model rychlosti.":
        "<b>Best</b> is the model time for the fastest route, <b>choice</b> is how much slower your route is at the same pace, <b>execution</b> is how much slower you were than your pace on the route you ran. Differences up to 20 s per leg are within the noise of the model. ✓ in the column model marks the legs from which your personal speed model learns.",
    "Běh z hodinek":
        "Run from the watch",
    "Start %(start)s, čas %(timer)s, %(km)s km <span class=\"stav %(cls)s\">shoda %(match)s</span>":
        "Start %(start)s, time %(timer)s, %(km)s km <span class=\"stav %(cls)s\">match %(match)s</span>",
    "K závodu není spárovaný žádný běh ze dne %(date)s.":
        "No run from %(date)s is matched with the race.",
    "Běh z hodinek (.fit, nebo zip z Garmin Connect)":
        "Run from the watch (.fit, or a zip from Garmin Connect)",
    "Běh nahraný tady se spáruje rovnou s tímhle závodem. Víc běhů najednou nebo celý export z Garminu: <a href=\"%(upload)s\">Nahrát běhy</a>.":
        "A run uploaded here is matched straight away with this race. Several runs at once or a whole Garmin export: <a href=\"%(upload)s\">Upload runs</a>.",
    "<b>Mapa:</b> nejlepší je <b>1. KMZ z Livelox</b>. Když ho Livelox stáhnout nedovolí, <b>2. dva snímky z Livelox</b>, jinak <b>3. fotka papírové mapy</b>. <a href=\"%(help)s#livelox\">Jak na to</a>":
        "<b>Map:</b> the best is <b>1. a KMZ from Livelox</b>. When Livelox does not allow the download, <b>2. two screenshots from Livelox</b>, otherwise <b>3. a photo of the paper map</b>. <a href=\"%(help)s#livelox\">How to</a>",
    "1. Mapa s tratí (KMZ) <span class=\"badge badge-tichy\">kategorie %(name)s</span>":
        "1. Map with course (KMZ) <span class=\"badge badge-tichy\">class %(name)s</span>",
    "nahraná":
        "uploaded",
    "chybí":
        "missing",
    "%(src)s, přesnost asi ±%(acc)s m":
        "%(src)s, accuracy about ±%(acc)s m",
    "z obrázku":
        "from an image",
    "z fotky":
        "from a photo",
    "z fotky usazené ručně":
        "from a photo placed by hand",
    "ze snímku Livelox":
        "from a Livelox screenshot",
    "Z ní se čtou kontroly a jejich pořadí.":
        "The controls and their order are read from it.",
    "když se fotka neusadila, nebo sedí špatně":
        "when the photo was not placed, or is placed wrongly",
    "KMZ z Livelox: Mapa s tratí":
        "KMZ from Livelox: Map with course",
    "Mapa závodu je posunutá ručně o %(m)s m.":
        "The map of the race is shifted by hand by %(m)s m.",
    "Vrátit původní usazení":
        "Restore the original placement",
    "Leží celá mapa vedle tvé stopy (všechny kontroly posunuté stejně)? <a href=\"%(fix)s\">Usadit mapu ručně podle kontrol</a>. Když zlobí GPS jen na pár úsecích, oprav si stopu u úseku.":
        "Is the whole map lying beside your track (all controls shifted the same way)? <a href=\"%(fix)s\">Place the map by hand by the controls</a>. When the GPS misbehaves only on a few legs, correct the track at the leg.",
    "1. Mapa bez tratě (KMZ) <span class=\"badge badge-tichy\">sdílená pro celý závod</span>":
        "1. Map without course (KMZ) <span class=\"badge badge-tichy\">shared for the whole race</span>",
    "ze snímku Livelox, přesnost asi ±%(acc)s m, %(res)s m na pixel":
        "from a Livelox screenshot, accuracy about ±%(acc)s m, %(res)s m per pixel",
    "nahrál %(who)s":
        "uploaded by %(who)s",
    "Z ní se čte terén pro nejlepší postupy. Stačí, když ji nahraje jeden člověk z oddílu.":
        "The terrain for the best routes is read from it. It is enough if one person from the club uploads it.",
    "KMZ z Livelox: Pouze mapa":
        "KMZ from Livelox: Map only",
    "KMZ bez tratě nahradí mapu ze snímku a nejlepší postupy se přepočítají.":
        "A KMZ without course replaces the map from a screenshot and the best routes are recomputed.",
    "2. Dva snímky z Livelox <span class=\"badge badge-tichy\">když KMZ stáhnout nejde</span>":
        "2. Two screenshots from Livelox <span class=\"badge badge-tichy\">when the KMZ cannot be downloaded</span>",
    "Snímek obrazovky mapy s tratí a druhý ze stejného pohledu s vypnutou tratí. Z prvního se čtou kontroly, z druhého terén pro nejlepší postupy (jako z KMZ bez tratě).":
        "A screenshot of the map with the course and a second one from the same view with the course switched off. The controls are read from the first, the terrain for the best routes from the second (as from a KMZ without course).",
    "<span class=\"stav ob-ok\">snímek s tratí uložený</span> %(w)s × %(h)s px; snímek bez tratě ze stejného pohledu můžeš nahrát i sám.":
        "<span class=\"stav ob-ok\">screenshot with course saved</span> %(w)s × %(h)s px; you can also upload the screenshot without course from the same view on its own.",
    "Snímek z Livelox s tratí":
        "Livelox screenshot with course",
    "Snímek z Livelox bez tratě (stejný pohled)":
        "Livelox screenshot without course (the same view)",
    "Jak snímky udělat v Chromu (6 kroků): <a href=\"%(help)s#snimky\">Jak na to</a>. Jen pro vlastní rozbor, nesdílej je dál.":
        "How to take the screenshots in Chrome (6 steps): <a href=\"%(help)s#snimky\">How to</a>. For your own analysis only, do not share them.",
    "3. Fotka papírové mapy <span class=\"badge badge-tichy\">když nejde nic z toho</span>":
        "3. Photo of the paper map <span class=\"badge badge-tichy\">when nothing else works</span>",
    "Z fotky se čtou jen kontroly; nejlepší postupy z ní nebudou (terén se z ní spolehlivě přečíst nedá).":
        "Only the controls are read from a photo; there will be no best routes from it (the terrain cannot be read reliably from it).",
    "Fotka nebo obrázek mapy s tratí (jpg, png)":
        "Photo or image of the map with course (jpg, png)",
    "Celou mapu shora, za světla a bez blesku, mapu polož rovně a nic ať nezakrývá kontroly. Fotka se na místo usadí sama podle kontrol a tvé stopy v oficiálních časech ražení (potřebuje běh z hodinek a mezičasy z ORIS).":
        "The whole map from above, in daylight and without flash, lay the map flat and let nothing cover the controls. The photo places itself by the controls and your track at the official punch times (it needs the run from the watch and the splits from ORIS).",
    "Nahrát vybrané soubory":
        "Upload the chosen files",
    "Soubory jde do polí i přetáhnout myší. Analýza se po nahrání spustí sama.":
        "Files can also be dragged into the fields with the mouse. The analysis starts on its own after the upload.",
    "Otevřít závod v Livelox":
        "Open the race in Livelox",
    "V Livelox:":
        "In Livelox:",
    "vyber závod a kategorii, v zobrazení mapy vpravo nahoře tři čárky → Stáhnout mapu. Dvakrát: Mapa s tratí (KMZ) a Pouze mapa (KMZ). Mapy vidí jen přihlášení členové a nejdou z aplikace stáhnout.":
        "choose the race and the class, in the map view at the top right the three bars → Download map. Twice: Map with course (KMZ) and Map only (KMZ). Maps are visible only to logged-in members and cannot be downloaded from the app.",
    "Vybrat jiný běh z toho dne":
        "Choose another run from that day",
    "automaticky":
        "automatically",
    "%(km)s km od centra":
        "%(km)s km from the centre",
    "Použít":
        "Use",
    "Analýza se spouští sama po každé změně podkladů. Ručně je potřeba jen výjimečně.":
        "The analysis starts on its own after every change of the source files. Doing it by hand is needed only exceptionally.",
    "Spustit analýzu znovu":
        "Run the analysis again",
    "Závod ORIS":
        "ORIS race",
    "Tenhle závod v seznamu svých závodů nemáš, takže k němu zatím není žádný rozbor.":
        "You do not have this race in your list of races, so there is no analysis of it yet.",
    "Rozbor vznikne, když jsi závod běžel a je v ORIS pod tvým registračním číslem. Potom stačí nahrát běh z hodinek (.fit) a mapu.":
        "An analysis appears when you ran the race and it is in ORIS under your registration number. Then it is enough to upload the run from the watch (.fit) and the map.",
    "Načíst moje závody z ORIS":
        "Load my races from ORIS",
    "Závod na klubovém webu":
        "Race on the club website",
    "Nový závod":
        "New race",
    "Přidat závod ručně":
        "Add a race by hand",
    "Pro závody, které nejsou v ORIS (zahraničí, tréninky). České závody se načtou z ORIS samy; závod z ORIS, na který nejsi přihlášený pod svou registračkou, přidáš <a href=\"%(url)s\">z ORIS podle čísla</a>.":
        "For races that are not in ORIS (abroad, training). Czech races are loaded from ORIS on their own; a race from ORIS you are not entered in under your registration number you add <a href=\"%(url)s\">from ORIS by its number</a>.",
    "Název":
        "Name",
    "Oficiální čas":
        "Official time",
    "Čas slouží ke spárování s během z hodinek. Mezičasy se u ručního závodu berou z GPS.":
        "The time is used to match the run from the watch. For a race added by hand the splits are taken from the GPS.",
    "Přidat":
        "Add",
    "Přidat závod z ORIS":
        "Add a race from ORIS",
    "Pro závod z ORIS, kde nejsi v přihláškách pod svou registračkou (běžel jsi za někoho, na místě, jinou kategorii). Závody, na které jsi přihlášený, se načtou samy.":
        "For a race from ORIS where you are not among the entries under your registration number (you ran for somebody, on the spot, in another class). Races you are entered in are loaded on their own.",
    "Číslo závodu v ORIS nebo odkaz":
        "Race number in ORIS or a link",
    "Najít závod":
        "Find the race",
    "závod v ORIS":
        "race in ORIS",
    "Tenhle závod už mezi svými závody máš (kategorie %(name)s): <a href=\"%(url)s#kategorie\">otevřít</a>. Kategorii změníš na jeho stránce.":
        "You already have this race among your races (class %(name)s): <a href=\"%(url)s#kategorie\">open</a>. You change the class on its page.",
    "Kategorie, kterou jsi běžel":
        "The class you ran",
    "Oficiální čas a mezičasy se vezmou z výsledků kategorie, když v nich jsi; jinak z GPS.":
        "The official time and splits are taken from the results of the class when you are in them; otherwise from the GPS.",
    "Závod v ORIS nemá žádné kategorie.":
        "The race has no classes in ORIS.",
    "Závody z ORIS a ručně přidané. U každého je vidět, co ještě chybí k rozboru.":
        "Races from ORIS and added by hand. For each you can see what is still missing for the analysis.",
    "ORIS načten %(when)s.":
        "ORIS loaded %(when)s.",
    "Závody z ORIS se načtou samy, když v <a href=\"%(url)s\">Profilu</a> zadáš svoje registrační číslo ORIS. Bez něj můžeš závod přidat z ORIS nebo ručně.":
        "Races from ORIS are loaded on their own once you enter your ORIS registration number in your <a href=\"%(url)s\">Profile</a>. Without it you can add a race from ORIS or by hand.",
    "Poslední načtení z ORIS se nepovedlo: %(error)s":
        "The last load from ORIS failed: %(error)s",
    "Načíst závody z ORIS":
        "Load races from ORIS",
    "Sezóna":
        "Season",
    "všechny":
        "all",
    "Hledat závod":
        "Search for a race",
    "v sezóně %(season)s":
        "in the season %(season)s",
    "s hotovým rozborem":
        "with a finished analysis",
    "čeká na mapu nebo běh z hodinek":
        "waiting for a map or a run from the watch",
    "Poslední rozbor":
        "Last analysis",
    "Otevřít rozbor":
        "Open the analysis",
    "Filtr podle stavu":
        "Filter by status",
    "Vše":
        "All",
    "S během":
        "With a run",
    "Chybí mapa":
        "Map missing",
    "Chybí aktivita":
        "Activity missing",
    "Tomuhle filtru žádný závod neodpovídá.":
        "No race matches this filter.",
    "Zatím tu nejsou žádné závody. Tenhle účet nemá registrační číslo ORIS, takže se z něj nenačtou: přidej závod ručně.":
        "There are no races here yet. This account has no ORIS registration number, so no races are loaded for it: add a race by hand.",
    "Zatím tu nejsou žádné závody. Načti je z ORIS tlačítkem nahoře, nebo přidej závod ručně.":
        "There are no races here yet. Load them from ORIS with the button above, or add a race by hand.",
    "<a href=\"%(url)s\">Jak na to</a>: kde vzít mapy z Livelox a běhy z Garminu.":
        "<a href=\"%(url)s\">How to</a>: where to get maps from Livelox and runs from Garmin.",
    "Kat.":
        "Class",
    "Aktivita":
        "Activity",
    "Mapa bez tratě":
        "Map without course",
    "je":
        "present",
    "Doplnit podklady":
        "Add source files",
    "Účet se zakládá registračním číslem ORIS. Jméno a tvoje závody se podle něj načtou samy.":
        "The account is created with an ORIS registration number. Your name and your races are loaded from it on their own.",
    "Tři písmena oddílu a čtyři číslice, např. BFM0000. Je to i tvoje přihlašovací jméno a později ho nejde změnit.":
        "Three club letters and four digits, e.g. BFM0000. It is also your login name and cannot be changed later.",
    "Kód od správce":
        "Code from the administrator",
    "Kód patří k tvému registračnímu číslu a dostaneš ho od správce aplikace. Díky němu si účet na tvoje číslo nezaloží nikdo jiný.":
        "The code belongs to your registration number and you get it from the administrator of the app. Thanks to it nobody else can create an account for your number.",
    "Heslo (aspoň 8 znaků)":
        "Password (at least 8 characters)",
    "Heslo znovu":
        "Password again",
    "Založit účet":
        "Create the account",
    "Už účet máš? <a href=\"%(url)s\">Přihlásit</a>":
        "Already have an account? <a href=\"%(url)s\">Log in</a>",
    "Oříznout snímek z Livelox":
        "Crop the screenshot from Livelox",
    "Kde na snímku končí mapa a začíná stránka Livelox, aplikace nepoznala jistě. Zkontroluj obdélník.":
        "The app could not tell for certain where the map ends and the Livelox page begins on the screenshot. Check the rectangle.",
    "Obdélník ukazuje, co ze snímku je mapa. <b>Přetáhni jeho rohy tak, aby obsahoval celou mapu, ale ne lištu, seznam běžců ani tlačítka Livelox.</b> Šedé pozadí kolem mapy nevadí. Totéž oříznutí dostane i snímek bez tratě.":
        "The rectangle shows what part of the screenshot is the map. <b>Drag its corners so that it contains the whole map but not the bar, the list of runners or the Livelox buttons.</b> A grey background around the map does not matter. The screenshot without the course gets the same crop.",
    "Snímek s tratí; rohy obdélníku jdou přetáhnout":
        "Screenshot with course; the corners of the rectangle can be dragged",
    "Celý snímek":
        "Whole screenshot",
    "Oříznout a usadit znovu":
        "Crop and place again",
    "Snímky se usadí znovu s tímhle oříznutím a mapa bez tratě se uloží znovu; analýza se pak spustí sama.":
        "The screenshots are placed again with this crop and the map without course is saved again; the analysis then starts on its own.",
    "Snímky se usadí znovu s tímhle oříznutím; analýza se pak spustí sama.":
        "The screenshots are placed again with this crop; the analysis then starts on its own.",
    "Soubory .fit nebo .zip (jde vybrat víc najednou)":
        "Files .fit or .zip (several can be chosen at once)",
    "Jednotlivé soubory <b>.fit</b> z hodinek, nebo celý <b>export účtu Garmin</b> (zip z Garmin Connect, Správa dat, Export dat). Běhy se samy spárují se závody podle data, času startu a vzdálenosti od centra závodu. Z celého exportu se navíc spočítá tvůj model kopců; nahraný zip se potom smaže a zůstanou jen běhy spárované se závody a běhy ze dne a místa závodu, které se nespárovaly (ty přiřadíš nebo smažeš níže). Před párováním se z ORIS načtou tvoje závody. Smazané běhy se vrátí jen opětovným nahráním exportu. Velký export se nahrává i několik minut.":
        "Single <b>.fit</b> files from the watch, or a whole <b>Garmin account export</b> (a zip from Garmin Connect, Data Management, Export Your Data). Runs are matched with races on their own by the date, the start time and the distance from the centre of the race. From the whole export your hill model is also computed; the uploaded zip is then deleted and only the runs matched with races and the runs from the day and place of a race that were not matched stay (you assign or delete those below). Before the matching your races are loaded from ORIS. Deleted runs come back only by uploading the export again. A large export takes several minutes to upload.",
    "Nahrané aktivity (%(total)s)":
        "Uploaded activities (%(total)s)",
    "Start":
        "Start",
    "Sport":
        "Sport",
    "ano":
        "yes",
    "ne":
        "no",
    "nespárované u závodu":
        "unmatched at a race",
    "Použít tenhle běh jako stopu závodu":
        "Use this run as the track of the race",
    "Přiřadit: %(name)s":
        "Assign: %(name)s",
    "Zatím nic. Nahraj první běh.":
        "Nothing yet. Upload your first run.",
    "Ztratil jsem se":
        "I got lost",
    "jak to funguje":
        "how it works",
    "<b>Rozbor „Ztratil jsem se u kontroly“ je po závodě.</b> Až závod poběžíš, nahraj běh (.fit): stránka ukáže místa u kontrol, kde ses podle stopy zdržel, a jak ses měl vrátit. Na závodě se mobil ani jiné pomůcky používat nesmějí.":
        "<b>The analysis “I got lost at a control” is after the race.</b> When you have run the race, upload the run (.fit): the page shows the places at the controls where you lingered according to the track, and how you should have got back. A phone or other aids must not be used in a race.",
    "Nápověda potřebuje <b>mapu s tratí i mapu bez tratě</b> (KMZ, snímky z Livelox nebo fotku). Nahraj je v <a href=\"%(url)s#podklady\">Podkladech</a>; běh (.fit) k tomu potřeba není.":
        "The help needs <b>a map with course and a map without course</b> (a KMZ, Livelox screenshots or a photo). Upload them in <a href=\"%(url)s#podklady\">Source files</a>; a run (.fit) is not needed for it.",
    "<b>Připravuju mapu kolem kontrol.</b> Dělá se jednou pro závod (a znovu po nové analýze nebo usazení mapy), trvá asi minutu. Stránka se sama obnoví.":
        "<b>Preparing the map around the controls.</b> It is done once for a race (and again after a new analysis or placing of the map), it takes about a minute. The page refreshes itself.",
    "Mapu kolem kontrol se nepodařilo připravit: %(error)s":
        "The map around the controls could not be prepared: %(error)s",
    "Mapu kolem kontrol se nepodařilo připravit.":
        "The map around the controls could not be prepared.",
    "Režim":
        "Mode",
    "Kde jsem asi byl":
        "Where I probably was",
    "Mapa; ťukni, kde jsi asi byl":
        "Map; tap where you probably were",
    "Vyber kontrolu a ťukni do mapy, kde jsi asi byl, když ses ztratil.":
        "Choose a control and tap the map where you probably were when you got lost.",
    "Jak moc si nejsi jistý, kde jsi byl":
        "How unsure you are where you were",
    "Nejistota":
        "Uncertainty",
    "Místa do 100 m od kontroly, kde jsi zpomalil, kroužil nebo se otočil:":
        "Places within 100 m of the control where you slowed down, circled or turned:",
    "Záchytné body kolem":
        "Relocating features around",
    "(nepovinné, ručně, třeba „kupka, severní úpatí“)":
        "(optional, by hand, e.g. “knoll, north foot”)",
    "Rozbor po závodě: co bylo kolem kontroly a jak ses z místa, kde ses ztratil, měl vrátit. Rada je odhad z kresby mapy (cesty, vodoteče, ploty, okraje ploch, budovy), bez vrstevnic a skal. „Nedalo se minout“ znamená, že na tu věc bys narazil odkudkoli z kruhu nejistoty, kdybys šel daným směrem. Do oplocených a zakázaných míst rada nevede.":
        "An analysis after the race: what was around the control and how you should have got back from the place where you got lost. The advice is an estimate from the drawing of the map (paths, streams, fences, edges of areas, buildings), without contours and cliffs. “Could not be missed” means that you would hit that feature from anywhere in the circle of uncertainty if you went in the given direction. The advice does not lead into fenced and out-of-bounds places.",
    'V Garmin Connect za vybrané období není žádný běh.':
        'There is no run in Garmin Connect for the chosen period.',
    'Model kopců: staženo z Garmin Connect %(n)s běhů.':
        'Hill model: downloaded %(n)s runs from Garmin Connect.',
    'Nevybral jsi žádnou aktivitu ani model kopců.':
        'You selected no activity and no hill model.',
    'Stahuji z Garmin Connect: vybrané aktivity %(n)s, model kopců: %(model)s. Samy se spárují se závody.':
        'Downloading from Garmin Connect: selected activities %(n)s, hill model: %(model)s. They pair with your races on their own.',
    'Druh aktivity':
        'Activity type',
    'všechny druhy (%(n)s)':
        'all types (%(n)s)',
    'neznámý':
        'unknown',
    'Zaškrtnout vše zobrazené':
        'Select all shown',
    'Zrušit zaškrtnutí':
        'Clear selection',
    '<b>Spočítat i model kopců</b> <span class="ob-siroky">ze všech běhů</span> za období':
        '<b>Also fit the hill model</b> <span class="ob-siroky">from all runs</span> of the period',
    'Období modelu kopců':
        'Period for the hill model',
    'Zaškrtnuté běhy se uloží a zůstanou. K tomu appka stáhne všechny běhy za zvolené období a spočítá z nich, jak rychle běháš do kopce a z kopce, stejně jako z exportu účtu Garmin. Z nich zůstanou jen běhy ze závodů; ostatní (ukazují, kde bydlíš) se smažou. Obojí proběhne najednou.':
        'The runs you tick are saved and stay. On top of that the app downloads all runs of the chosen period and works out how fast you run uphill and downhill, as from a Garmin account export. Of those only the race runs stay; the others (they show where you live) are deleted. Both happen in one go.',
    'Načíst z Garmin Connect':
        'Load from Garmin Connect',
    'Běhy přímo z tvého účtu Garmin, bez ručního exportu':
        'Runs straight from your Garmin account, without a manual export',
    'Co tlačítko udělá':
        'What the button does',
    'Načíst vybrané a model kopců':
        'Load selected and hill model',
    'Zaškrtnuto':
        'Selected',
    # Garmin Connect (Personal API)
    'Tohle nevypadá jako klíč Personal API z Garmin Connect. Zkopíruj ho celý.':
        'This does not look like a Garmin Connect Personal API key. Copy all of it.',
    'Účet Garmin není připojený: vlož klíč Personal API.':
        'No Garmin account is connected: paste a Personal API key.',
    'Garmin vrátil neznámou odpověď místo přístupového tokenu.':
        'Garmin sent an unknown answer instead of an access token.',
    'Garmin Connect není dostupný (internet?): %(e)s':
        'Garmin Connect cannot be reached (internet?): %(e)s',
    'Garmin klíč nepřijal (je špatně zkopírovaný, vypršel, nebo byl smazaný). Vytvoř v Garmin Connect nový a vlož ho znovu.':
        'Garmin did not accept the key (it was copied wrong, has expired or was deleted). Create a new one in Garmin Connect and paste it again.',
    'Garmin Connect odpověděl chybou %(status)s při přihlášení klíčem.':
        'Garmin Connect answered with error %(status)s when signing in with the key.',
    'Garmin teď nechce odpovídat (příliš mnoho dotazů). Zkus to za chvíli.':
        'Garmin is not answering right now (too many requests). Try again in a while.',
    'Garmin přístup odmítl. Vytvoř v Garmin Connect nový klíč a vlož ho znovu.':
        'Garmin refused access. Create a new key in Garmin Connect and paste it again.',
    'Garmin Connect odpověděl chybou %(status)s.':
        'Garmin Connect answered with error %(status)s.',
    'Neplatné číslo aktivity.':
        'Invalid activity number.',
    'Aktivita %(aid)s: Garmin neposlal soubor .fit.':
        'Activity %(aid)s: Garmin sent no .fit file.',
    'stahuji z Garmin Connect %(i)s/%(n)s':
        'downloading from Garmin Connect %(i)s/%(n)s',
    'Garmin vrátil seznam aktivit, kterému appka nerozumí.':
        'Garmin sent a list of activities the app does not understand.',
    ' Nestaženo %(n)s: %(why)s':
        ' Not downloaded: %(n)s: %(why)s',
    'Staženo z Garmin Connect %(n)s aktivit, nových %(new)s.':
        'Downloaded %(n)s activities from Garmin Connect, %(new)s new.',
    'Nevybraná žádná aktivita.':
        'No activity selected.',
    'Z Garmin Connect se nestáhla žádná aktivita.':
        'No activity was downloaded from Garmin Connect.',
    'Klíč je uložený jen v tomhle počítači. Appka teď načte tvoje aktivity z Garmin Connect.':
        'The key is stored on this computer only. The app now loads your activities from Garmin Connect.',
    'Klíč je z tohoto počítače smazaný. V Garmin Connect ho můžeš smazat i tam.':
        'The key is deleted from this computer. You can delete it in Garmin Connect too.',
    'Nevybral jsi žádnou aktivitu.':
        'You did not select any activity.',
    'Běhy z Garmin Connect':
        'Runs from Garmin Connect',
    'poslední 2 týdny':
        'last 2 weeks',
    'poslední 2 měsíce':
        'last 2 months',
    'poslední rok':
        'last year',
    'všechno':
        'everything',
    'Zpět na Nahrát běhy':
        'Back to Upload runs',
    'Appka si běhy stáhne přímo z tvého účtu Garmin Connect, bez ručního exportu. Potřebuje k tomu <b>klíč Personal API</b>, který si vytvoříš sám v Garmin Connect. Heslo k účtu Garmin appka nikdy nedostane.':
        'The app downloads your runs straight from your Garmin Connect account, with no manual export. It needs a <b>Personal API key</b>, which you create yourself in Garmin Connect. The app never gets your Garmin password.',
    'Otevři v prohlížeči <a href="%(url)s" target="_blank" rel="noopener">Garmin Connect, Nastavení, Personal API</a> a přihlas se.':
        'Open <a href="%(url)s" target="_blank" rel="noopener">Garmin Connect, Settings, Personal API</a> in your browser and sign in.',
    'Klikni na <b>Create Key</b>, potvrď podmínky a vyber platnost (nejdéle jeden rok).':
        'Click <b>Create Key</b>, accept the terms and choose how long it is valid (one year at most).',
    'Klíč zkopíruj (Garmin ho ukáže jen jednou) a vlož ho sem.':
        'Copy the key (Garmin shows it only once) and paste it here.',
    'Klíč Personal API':
        'Personal API key',
    'Připojit účet Garmin':
        'Connect Garmin account',
    'Klíč se uloží jen do datové složky appky v tomhle počítači a posílá se jen Garminu. Kdo má klíč, může číst tvoje data z Garmin Connect, takže ho nikomu neposílej. Když klíč vyprší nebo ho v Garmin Connect smažeš, appka řekne, ať vložíš nový.':
        "The key is stored only in the app's data folder on this computer and is sent only to Garmin. Anyone with the key can read your Garmin Connect data, so do not send it to anyone. When the key expires or you delete it in Garmin Connect, the app asks you for a new one.",
    'Období':
        'Period',
    'Ukázat':
        'Show',
    'Předvybrané jsou běhy, které v appce ještě nejsou. Načtené běhy se samy spárují se závody.':
        'Runs that are not in the app yet are selected. Loaded runs pair with your races on their own.',
    'V appce':
        'In the app',
    'Načíst %(name)s':
        'Load %(name)s',
    'Načíst vybrané':
        'Load selected',
    'Za tohle období nejsou v Garmin Connect žádné aktivity.':
        'There are no activities in Garmin Connect for this period.',
    'Účet Garmin je připojený klíčem uloženým jen v tomhle počítači.':
        'The Garmin account is connected with a key stored on this computer only.',
    'Odpojit účet Garmin':
        'Disconnect Garmin account',
    '<b>Nejjednodušší: přímo z Garmin Connect.</b> V <a href="%(url)s">Nahrát běhy, Načíst přímo z Garmin Connect</a> vložíš klíč Personal API, který si vytvoříš v <a href="https://connect.garmin.com/app/settings/personalApiToken" target="_blank" rel="noopener">nastavení Garmin Connect</a> (Create Key). Appka pak sama ukáže tvoje běhy, stáhne vybrané a spočítá i model kopců. Klíč zůstane jen v tomhle počítači. Ruční export níže už nepotřebuješ.':
        '<b>Easiest: straight from Garmin Connect.</b> In <a href="%(url)s">Upload runs, Load straight from Garmin Connect</a> you paste a Personal API key, which you create in the <a href="https://connect.garmin.com/app/settings/personalApiToken" target="_blank" rel="noopener">Garmin Connect settings</a> (Create Key). The app then lists your runs, downloads the ones you pick and fits your hill model too. The key stays on this computer only. You no longer need the manual export below.',
    '<b>Nejjednodušší: přímo z Garmin Connect.</b> V Nahrát běhy, Načíst přímo z Garmin Connect vložíš klíč Personal API, který si vytvoříš v <a href="https://connect.garmin.com/app/settings/personalApiToken" target="_blank" rel="noopener">nastavení Garmin Connect</a> (Create Key). Appka pak sama ukáže tvoje běhy, stáhne vybrané a spočítá i model kopců. Klíč zůstane jen v tomhle počítači. Ruční export níže už nepotřebuješ.':
        '<b>Easiest: straight from Garmin Connect.</b> In Upload runs, Load straight from Garmin Connect you paste a Personal API key, which you create in the <a href="https://connect.garmin.com/app/settings/personalApiToken" target="_blank" rel="noopener">Garmin Connect settings</a> (Create Key). The app then lists your runs, downloads the ones you pick and fits your hill model too. The key stays on this computer only. You no longer need the manual export below.',
    'Načíst přímo z Garmin Connect':
        'Load straight from Garmin Connect',
    'Bez ručního exportu: appka si běhy stáhne z tvého účtu Garmin klíčem, který vložíš jen sem.':
        'No manual export: the app downloads runs from your Garmin account with a key you paste only here.',
    'Oříznutí stopy se nezměnilo.':
        'The cut of the track has not changed.',
    'Po oříznutí by zbyla méně než minuta stopy. Nic se neuložilo.':
        'Less than a minute of the track would be left. Nothing was saved.',
    ' Analýza se přepočítá na pozadí.':
        ' The analysis will be redone in the background.',
    'Začátek a konec GPS stopy':
        'Start and end of the GPS track',
    ': oříznuto':
        ': cut',
    'Uříznutá část je v mapě šedě čárkovaně.':
        'The part cut off is grey and dashed on the map.',
    'Uprostřed stopy chybí GPS: v %(at)s na %(dur)s min (rovná čára %(dist)s m). Tam se nic neořezává, úseky by přišly o čas. Když tě rovná čára na úseku ruší, otevři úsek a dej <b>Opravit moji stopu</b>.':
        'The GPS is missing in the middle of the track: at %(at)s for %(dur)s min (a straight line of %(dist)s m). Nothing is cut there, the legs would lose time. If the straight line bothers you on a leg, open the leg and choose <b>Correct my track</b>.',
    'uřízne jen skok GPS na začátku nebo na konci, dobrá stopa zůstane celá':
        'cuts off only a GPS jump at the start or at the end, a good track stays whole',
    'neořezávat':
        'do not cut',
    'použije se celá stopa, jak ji hodinky zapsaly':
        'the whole track is used as the watch recorded it',
    'ručně':
        'by hand',
    'začátek a konec nastavíš posuvníky':
        'set the start and the end with the sliders',
    'Stopa začíná v':
        'The track starts at',
    'Stopa končí v':
        'The track ends at',
    'Čas je od prvního bodu GPS, celkem %(total)s. Šedá čárkovaná část v mapě se uřízne; začátek stopy je bod, odkud se počítá start (když závod nemá mezičasy z ORIS).':
        'Time from the first GPS point, %(total)s in all. The grey dashed part on the map is cut off; the start of the track is where the start is counted from (when the race has no split times in ORIS).',
    'Uložit a přepočítat':
        'Save and recompute',
    'Vrátit to jde kdykoli: vyber „automaticky“ a ulož.':
        'You can undo it at any time: choose “automatically” and save.',
    # merged from the branch chain of 2026-11-01 (watch over USB, race file, data folder, revize)
    'Uložená fotka mapy už tu není; nahraj ji znovu.':
        'The saved map photo is no longer here; upload it again.',
    'Čekající snímky Livelox už tu nejsou; nahraj je znovu.':
        'The waiting Livelox screenshots are no longer here; upload them again.',
    'Terén „%(name)s“ běháš rychleji, než čeká mapový klíč (asi o %(pct)s %%).':
        'You run “%(name)s” faster than the map key expects (by about %(pct)s %%).',
    'Terén „%(name)s“ běháš pomaleji, než čeká mapový klíč (asi o %(pct)s %%).':
        'You run “%(name)s” slower than the map key expects (by about %(pct)s %%).',
    'V terénech, kde máš dost dat, běháš zhruba tak, jak čeká mapový klíč.':
        'In the terrain where you have enough data you run about as the map key expects.',
    'Model stojí na %(n)s závodě':
        'The model rests on %(n)s race',
    'Model stojí na %(n)s závodech':
        'The model rests on %(n)s races',
    ', je zatím jen orientační.':
        ', so it is only a rough guide so far.',
    'Do kopce: 1 m stoupání tě stojí jako %(k)s m po rovině (učebnice počítá asi %(book)s m),':
        'Uphill: 1 m of climb costs you as much as %(k)s m on the flat (the textbook says about %(book)s m),',
    'takže jsi do kopce silnější než průměr.':
        'so you are stronger uphill than average.',
    ', už je docela spolehlivý.':
        ', it is fairly reliable by now.',
    'takže jsi do kopce slabší než průměr.':
        'so you are weaker uphill than average.',
    'zhruba jako průměr.':
        'about average.',
    'Fotka je uložená a usazuje se na pozadí; výsledek uvidíš v úlohách.':
        'The photo is saved and is being placed in the background; you will see the result in the jobs.',
    'Snímek bez tratě je uložený. Až nahraješ snímek s tratí ze stejného pohledu, zpracují se společně.':
        'The screenshot without the course is saved. Once you upload the screenshot with the course from the same view, they are processed together.',
    'Snímky z Livelox jsou uložené a usazují se na pozadí podle běhu a mezičasů. Výsledek uvidíš v úlohách.':
        'The Livelox screenshots are saved and are being placed in the background using the run and the split times. You will see the result in the jobs.',
    'Snímky z Livelox jsou uložené. Jakmile bude k dispozici běh z hodinek a mezičasy z ORIS, usadí se automaticky.':
        'The Livelox screenshots are saved. They are placed automatically once the watch run and the ORIS split times are here.',
    'Obrázek jde nahrát jen jako mapu s tratí. Mapu bez tratě nahraj jako KMZ z Livelox.':
        'An image can only be uploaded as the map with the course. Upload the map without the course as a KMZ from Livelox.',
    'Fotka je uložená. Až doplníš běh z hodinek a mezičasy z ORIS, usadí se automaticky.':
        'The photo is saved. It is placed automatically once you add the watch run and the ORIS split times.',
    'Uloženo: %(regno)s patří v ORIS jménu %(name)s. Závody z ORIS se načítají. Když to nejsi ty, napiš autorovi aplikace.':
        'Saved: %(regno)s belongs to %(name)s in ORIS. Your races are being loaded from ORIS. If that is not you, write to the author of the app.',
    'Mapa bez tratě je uložená.':
        'The map without the course is saved.',
    'Složka neexistuje.':
        'The folder does not exist.',
    'Načteno běhů: %(n)s.':
        'Runs loaded: %(n)s.',
    'Složka neexistuje. Zkontroluj cestu.':
        'The folder does not exist. Check the path.',
    'Běhy se se závody spárovaly samy.':
        'The runs were matched to the races automatically.',
    'Už v aplikaci bylo %(n)s.':
        '%(n)s were already in the app.',
    '<b>Jak se pozná chyba.</b> U ostatních běžců jen z mezičasů: chyba je úsek, kde byl běžec o víc než 30 s a zároveň o víc než 25 %% pomalejší než jeho vlastní normál (metoda WinSplits). Pomalý běh celý závod tedy chybou není, jeden pomalý úsek být může. U tebe má aplikace i stopu z hodinek, a tak na záložce Mapa a úseky pozná i druh chyby (přeběhnutí, nedoběhnutí, úhyb ze směru, hledání v kruhu, zastavení a nové určení polohy). Pozdější startovní čas pomáhá (vyšlapané stopy), takže malé rozdíly neznamenají chybu.':
        '<b>How a mistake is found.</b> For the other runners only from the split times: a mistake is a leg where the runner was more than 30 s and at the same time more than 25 %% slower than their own normal (the WinSplits method). So running slowly the whole race is not a mistake, one slow leg can be. For you the app also has the watch track, so on the Map and legs tab it also tells the kind of mistake (overshoot, undershoot, drifting off the bearing, searching in circles, stopping and relocating). A later start time helps (trodden paths), so small differences do not mean a mistake.',
    'Webový režim':
        'Web mode',
    'Ke každému závodu appka potřebuje tři věci: běh z hodinek, mapu s tratí a mapu bez tratě. Časy a mezičasy si načte z ORIS sama. KMZ a fotku mapy můžeš nahrát kdykoliv; fotka počká, než bude k dispozici běh a mezičasy. Snímky obrazovky z Livelox můžeš také nahrát kdykoliv a každý zvlášť; aplikace počká na oba snímky, běh a mezičasy z ORIS.':
        'For every race the app needs three things: the run from the watch, the map with the course and the map without the course. It loads the times and split times from ORIS itself. You can upload a KMZ or a photo of the map at any time; the photo waits until the run and the split times are here. You can also upload Livelox screenshots at any time and each one separately; the app waits for both screenshots, the run and the ORIS split times.',
    'Obsah nápovědy':
        'Help contents',
    'Rychlý obsah':
        'Quick contents',
    'Dva snímky z Livelox':
        'Two Livelox screenshots',
    '<b>Rovnou z hodinek</b>: připoj hodinky kabelem k počítači, běhy jsou ve složce <code>GARMIN/Activity</code> jako soubory .fit.':
        '<b>Straight from the watch</b>: connect the watch to the computer with the cable, the runs are in the folder <code>GARMIN/Activity</code> as .fit files.',
    'V aplikaci v <a href="%(url)s">Nahrát běhy</a> klikni na <b>Načíst z hodinek přes USB nebo ze složky</b>: nabídnu jen běhy, které tu ještě nemáš. Novější hodinky (často na Macu) se připojují přes MTP a jako disk se neukážou. Tam běhy exportuj z Garmin Connect, jak je popsáno výše.':
        'In the app, in <a href="%(url)s">Upload runs</a>, click <b>Load from the watch over USB or from a folder</b>: only runs that are not here yet are offered. Newer watches (often on a Mac) connect over MTP and do not show up as a disk. There, export the runs from Garmin Connect as described above.',
    'Celý zip nahraj v <a href="%(url)s">Nahrát běhy</a>. Appka smaže svou dočasnou nahranou kopii ZIPu; soubor v počítači ti zůstane. V aplikaci si nechá jen běhy ze závodů.':
        'Upload the whole zip in <a href="%(url)s">Upload runs</a>. The app deletes its temporary uploaded copy of the ZIP; the file on your computer stays. The app keeps only the runs from races.',
    'Celý zip nahraj v Nahrát běhy. Appka smaže svou dočasnou nahranou kopii ZIPu; soubor v počítači ti zůstane. V aplikaci si nechá jen běhy ze závodů.':
        'Upload the whole zip in Upload runs. The app deletes its temporary uploaded copy of the ZIP; the file on your computer stays. The app keeps only the runs from races.',
    'Z mapy s tratí appka čte kontroly, z mapy bez tratě terén pro nejlepší postupy.':
        'From the map with the course the app reads the controls, from the map without the course the terrain for the best routes.',
    'Mapy zůstávají jen v tomhle počítači. Jsou dílem pořadatele: používej je jen pro vlastní rozbor.':
        "The maps stay only on this computer. They are the organiser's work: use them only for your own analysis.",
    'Mapu bez tratě stačí, když nahraje jeden člověk z oddílu. Mapy vidí jen přihlášení členové a z appky nejdou stáhnout.':
        'It is enough when one person from the club uploads the map without the course. Only signed-in members see the maps and they cannot be downloaded from the app.',
    'V kostce':
        'In short',
    'Závody v modelu, kontrola modelu a historie':
        'Races in the model, model check and history',
    'tři písmena oddílu a čtyři číslice, např. BFM0000':
        'three club letters and four digits, e.g. BFM0000',
    'Podle něj se z ORIS načtou tvoje závody a kategorie. Ověří se v ORIS a po uložení se ukáže jméno, ke kterému patří. Zadat ho jde jen jednou, tak ho zkontroluj.':
        'Your races and classes are loaded from ORIS by it. It is checked in ORIS and after saving the name it belongs to is shown. It can be entered only once, so check it.',
    'Podle registračního čísla se z ORIS načítají tvoje závody, kategorie, Livelox ID a oficiální mezičasy.':
        'Your races, classes, Livelox IDs and official split times are loaded from ORIS by the registration number.',
    'Účet k němu patří napořád, změnit ho nejde.':
        'The account belongs to it for good, it cannot be changed.',
    'Data a verze':
        'Data and version',
    'Verze aplikace':
        'App version',
    'Složka s daty':
        'Data folder',
    'Otevřít složku s daty':
        'Open the data folder',
    'Zkontrolovat nové vydání':
        'Check for a new release',
    'Aplikace sama nikam nevolá a nové verze nehledá: odkaz jen otevře stránku vydání v prohlížeči. Novou verzi nainstaluj přes starou, data ve složce zůstanou a závody budou vidět dál.':
        'The app does not call anywhere by itself and does not look for new versions: the link only opens the releases page in the browser. Install a new version over the old one, the data in the folder stays and the races remain visible.',
    'Smaže všechno, co je v aplikaci: závody (%(races)s), běhy z hodinek (%(activities)s), rozbory (%(analyses)s), poznámky (%(notes)s), osobní modely (%(models)s), mapy i registrační číslo ORIS. Nejde to vrátit.':
        'Deletes everything in the app: races (%(races)s), runs from the watch (%(activities)s), analyses (%(analyses)s), notes (%(notes)s), personal models (%(models)s), maps and the ORIS registration number. It cannot be undone.',
    'Pro potvrzení napiš SMAZAT':
        'To confirm, type SMAZAT',
    'Smazat všechna moje data':
        'Delete all my data',
    'Jak se ztráta počítá':
        'How the loss is computed',
    '<b>Ztráta</b> u úseku je rozdíl proti tvému nejlepšímu možnému běhu podle tvého modelu rychlosti: nejlepší postup a tvoje tempo bez zaváhání. Dělí se na <b>volbu postupu</b> (zvolil jsi pomalejší variantu) a <b>chybu</b> (bloudění, přeběhnutí, kroužení a dohledávání u kontroly, zastavení). Když stopa vypadá na bloudění, nebo se čas ztratil smyčkami u kontroly, počítá se to jako chyba, ne jako volba postupu.':
        'The <b>loss</b> on a leg is the difference from your best possible run by your speed model: the best route at your pace without hesitation. It is split into <b>route choice</b> (you chose a slower option) and <b>mistake</b> (getting lost, overshooting, circling and searching near the control, stopping). When the track looks like getting lost, or the time was lost in loops near the control, it counts as a mistake, not as route choice.',
    '<b>Mezičasy kategorie</b> měří něco jiného: o kolik jsi byl na úseku pomalejší než tvoje obvyklé tempo proti ostatním běžcům. Proto jsou čísla v mezičasech menší. Kde se model a mezičasy rozcházejí o víc než minutu, úsek to napíše; tam ber ztrátu z modelu s rezervou.':
        '<b>The class split times</b> measure something else: how much slower than your usual pace you were on the leg compared with the other runners. That is why the numbers in the split times are smaller. Where the model and the split times differ by more than a minute, the leg says so; take the loss from the model with a pinch of salt there.',
    'Mapa závodu je dílo pořadatele a mapaře a je chráněná autorským právem.':
        'The race map is the work of the organiser and the mapper and is protected by copyright.',
    'Zůstává jen v tomhle počítači; používej ji jen pro rozbor vlastního běhu a posílej ji nanejvýš ostatním účastníkům závodu.':
        'It stays only on this computer; use it only to analyse your own run and share it at most with other participants of the race.',
    'V aplikaci slouží jen přihlášeným členům oddílu k rozboru vlastního běhu; nejde stáhnout a nesmí se šířit dál.':
        'In the app it serves only the signed-in club members to analyse their own run; it cannot be downloaded and must not be shared further.',
    '1. KMZ z Livelox <span class="badge badge-tichy">nejpřesnější podklady</span>':
        '1. KMZ from Livelox <span class="badge badge-tichy">the most accurate source</span>',
    'Mapa s tratí · kategorie %(name)s':
        'Map with the course · class %(name)s',
    'Mapa bez tratě · sdílená pro celý závod':
        'Map without the course · shared for the whole race',
    'Z ní se čte terén pro nejlepší postupy.':
        'The terrain for the best routes is read from it.',
    'Snímek s tratí čeká na běh a mezičasy, nebo na zpracování.':
        'The screenshot with the course is waiting for the run and the split times, or for processing.',
    'Snímek bez tratě čeká na snímek s tratí ze stejného pohledu.':
        'The screenshot without the course is waiting for the screenshot with the course from the same view.',
    'Oba snímky můžeš nahrát najednou, nebo každý zvlášť a klidně před během. Aplikace je uloží a počká na FIT i mezičasy z ORIS. Musí jít o stejný pohled. <a href="%(help)s#snimky">Jak je udělat v Chromu</a>. Jen pro vlastní rozbor, nesdílej je dál.':
        'You can upload both screenshots at once, or each separately, even before the run. The app saves them and waits for the FIT and the ORIS split times. It has to be the same view. <a href="%(help)s#snimky">How to make them in Chrome</a>. Only for your own analysis, do not share them.',
    'Celou mapu shora, za světla a bez blesku, mapu polož rovně a nic ať nezakrývá kontroly. Fotka se na místo usadí podle kontrol a tvé stopy v oficiálních časech ražení. Můžeš ji nahrát kdykoliv; pokud ještě chybí běh nebo mezičasy z ORIS, počká uložená na jejich doplnění.':
        'The whole map from above, in daylight and without flash, laid flat with nothing covering the controls. The photo is placed by the controls and your track at the official punch times. You can upload it any time; if the run or the ORIS split times are still missing, it waits saved until they are added.',
    'Jak začít':
        'How to start',
    '<b>Registrační číslo ORIS</b> (nepovinné) zadej v <a href="%(profile)s">Profilu</a>: tvoje závody, kategorie a oficiální mezičasy se pak načtou samy. Bez něj přidáš závod <a href="%(oris)s">podle čísla v ORIS</a> nebo <a href="%(new)s">ručně</a>.':
        '<b>ORIS registration number</b> (optional): enter it in <a href="%(profile)s">Profile</a> and your races, classes and official split times load by themselves. Without it you add a race <a href="%(oris)s">by its ORIS number</a> or <a href="%(new)s">by hand</a>.',
    '<b>Běh z hodinek</b> (.fit nebo zip z Garmin Connect) nahraj v <a href="%(url)s">Nahrát běhy</a>. Se závodem se spáruje sám.':
        '<b>Run from the watch</b> (.fit or zip from Garmin Connect): upload it in <a href="%(url)s">Upload runs</a>. It is matched to the race by itself.',
    '<b>Mapy</b>: u závodu v Podkladech nahraj KMZ z Livelox, s tratí a bez ní. <a href="%(url)s">Jak na to</a>':
        '<b>Maps</b>: in the race\'s Inputs upload the KMZ from Livelox, with and without the course. <a href="%(url)s">How to</a>',
    'Načte z ORIS závody, na které jsi přihlášený pod svým registračním číslem':
        'Loads from ORIS the races you entered under your registration number',
    'Jeden závod podle jeho čísla v ORIS, třeba když jsi běžel pod jiným číslem':
        'One race by its ORIS number, e.g. when you ran under another number',
    'Závod uložený jiným běžcem (.obzavod)':
        'A race saved by another runner (.obzavod)',
    'Načíst závod ze souboru':
        'Load a race from a file',
    'Jednotlivé soubory <b>.fit</b> z hodinek, nebo celý <b>export účtu Garmin</b> (zip z Garmin Connect, Správa dat, Export dat). Běhy se samy spárují se závody podle data, času startu a vzdálenosti od centra závodu. Z celého exportu se navíc spočítá tvůj model kopců. Po zpracování aplikace smaže pouze nahranou dočasnou kopii ZIPu ze svého úložiště; původní soubor ve tvém počítači zůstává beze změny. V aplikaci zůstanou běhy spárované se závody a běhy ze dne a místa závodu, které se nespárovaly (ty přiřadíš nebo smažeš níže). Ostatní běhy se z aplikace smažou kvůli ochraně soukromí a vrátí se jen opětovným nahráním exportu. Před párováním se z ORIS načtou tvoje závody. Velký export se nahrává i několik minut.':
        'Single <b>.fit</b> files from the watch, or a whole <b>Garmin account export</b> (zip from Garmin Connect, Data Management, Export Your Data). The runs are matched to the races by date, start time and distance from the race centre. From a whole export your hill model is computed as well. After processing the app deletes only the temporary uploaded copy of the ZIP from its storage; the original file on your computer stays unchanged. The app keeps the runs matched to races and the runs from the day and place of a race that did not match (assign or delete them below). Other runs are deleted from the app for privacy and come back only by uploading the export again. Before matching, your races are loaded from ORIS. A big export takes several minutes to upload.',
    'Načíst z hodinek přes USB nebo ze složky':
        'Load from the watch over USB or from a folder',
    'Hodinky Garmin připojené kabelem jako disk, nebo složka se soubory .fit.':
        'A Garmin watch connected by cable as a disk, or a folder with .fit files.',
}

EN.update({
    "podle %(n)s z %(controls)s kontrol": "by %(n)s of %(controls)s controls",
    "%(app)s běží na %(url)s (ukončení: v nabídce Ukončit aplikaci, nebo Ctrl+C)":
        "%(app)s is running at %(url)s (to quit: Quit the app in the menu, or Ctrl+C)",
    "Aplikace se nespustila: %(error)s\nData: %(data)s":
        "The app did not start: %(error)s\nData: %(data)s",
})

EN_JS = {
    'Podrobnosti jsou nahoře na stránce.':
        'The details are at the top of the page.',
    'Zkusit znovu':
        'Try again',
    "Roh obdélníku":
        "Corner of the rectangle",
    "Mapa: %(w)s × %(h)s px ze snímku %(W)s × %(H)s px.":
        "Map: %(w)s × %(h)s px from a screenshot of %(W)s × %(H)s px.",
    "mapa © pořadatel závodu":
        "map © organiser of the race",
    "Kontrola %(n)s: ťukni do mapy, kde jsi asi byl, když ses ztratil.":
        "Control %(n)s: tap the map where you probably were when you got lost.",
    "Nejdřív vyber kontrolu nahoře.":
        "First choose a control at the top.",
    "Počítám…":
        "Computing…",
    "Mapa závodu se mezitím změnila; obnov stránku.":
        "The map of the race has changed meanwhile; reload the page.",
    "Radu se nepodařilo spočítat, zkus to znovu.":
        "The advice could not be computed, try again.",
    "Načítám…":
        "Loading…",
    "U téhle kontroly stopa nic takového neukazuje.":
        "At this control the track shows nothing like that.",
    "Místa se nepodařilo načíst.":
        "The places could not be loaded.",
    "Kudy zpět: %(way)s":
        "Way back: %(way)s",
    "Ukládám…":
        "Saving…",
    "Uloženo.":
        "Saved.",
    "Popis smazaný.":
        "Description deleted.",
    "Nepodařilo se uložit.":
        "Saving failed.",
    "Plánovaný postup: klikáním do mapy přidávej body od kontroly ke kontrole. Dvojklik nebo Hotovo uloží.":
        "Planned route: add points by clicking on the map from control to control. A double click or Done saves.",
    "Zakázaná čára: klikáním do mapy přidávej její body. Dvojklik nebo Hotovo uloží.":
        "Impassable line: add its points by clicking on the map. A double click or Done saves.",
    "Těžko překonatelná čára: klikáním do mapy přidávej její body. Dvojklik nebo Hotovo uloží.":
        "Hardly passable line: add its points by clicking on the map. A double click or Done saves.",
    "Občerstvovačka: klikni do mapy na místo, kde stála.":
        "Refreshment control: click on the map where it stood.",
    "Oprava stopy: klikáním do mapy přidávej body, kudy jsi na úseku opravdu běžel (začátek a konec jsou kontroly). Dvojklik nebo Hotovo uloží.":
        "Correcting the track: add points by clicking on the map where you really ran on the leg (the start and the end are controls). A double click or Done saves.",
    "Načítám stopu a postupy…":
        "Loading the track and routes…",
    "Data závodu se nepodařilo načíst.":
        "The data of the race could not be loaded.",
    "překážky © přispěvatelé OpenStreetMap":
        "obstacles © OpenStreetMap contributors",
    "Neuloženo…":
        "Not saved…",
    "Načítám obrázek mapy…":
        "Loading the image of the map…",
    "Obrázek mapy se nepodařilo načíst.":
        "The image of the map could not be loaded.",
    "přechod, most nebo podchod (OpenStreetMap): tudy se smí":
        "crossing, bridge or underpass (OpenStreetMap): it may be crossed here",
    "Těžko překonatelné (velmi pomalé).":
        "Hardly passable (very slow).",
    "Zakázaný přechod (sdílený pro závod).":
        "Impassable crossing (shared for the race).",
    "Přidal: %(by)s.":
        "Added by: %(by)s.",
    "Smazat":
        "Delete",
    "opraveno ručně":
        "corrected by hand",
    "ztráta %(t)s":
        "loss %(t)s",
    "stání %(s)s s":
        "standing %(s)s s",
    "Občerstvovačka: zastávky do 30 m od ní jsou záměrné.":
        "Refreshment control: stops within 30 m of it are deliberate.",
    "možnost %(n)s":
        "option %(n)s",
    "postup průměrného běžce: tobě by trval %(t)s":
        "route of the average runner: it would take you %(t)s",
    "náběhový bod před kontrolou (odhad z mapy): %(label)s":
        "attack point before the control (an estimate from the map): %(label)s",
    "zarážka za kontrolou (odhad z mapy): %(label)s":
        "catching feature beyond the control (an estimate from the map): %(label)s",
    "tudy vede tvoje stopa, nejlepší postup tudy nesmí":
        "your track goes here, the best route must not",
    "tudy vede tvůj plán, nejlepší postup tudy nesmí":
        "your plan goes here, the best route must not",
    "tady jsi opustil přímý směr ke kontrole":
        "here you left the direct line to the control",
    "nejbližší záchytný bod při bloudění":
        "nearest relocating feature when you were lost",
    "Celá trať":
        "Whole course",
    "Zrušit výběr úseku a ukázat celou trať (Esc)":
        "Clear the leg selection and show the whole course (Esc)",
    "volba postupu %(t)s":
        "route choice %(t)s",
    "chyby v provedení %(t)s":
        "mistakes in execution %(t)s",
    "odhad ztráty z GPS %(t)s":
        "estimated loss from the GPS %(t)s",
    "únava %(t)s":
        "fatigue %(t)s",
    "Ztráta celkem <b>%(sum)s</b>:":
        "Total loss <b>%(sum)s</b>:",
    "Záměrné zastávky %(t)s se jako chyba nepočítají.":
        "Deliberate stops %(t)s do not count as a mistake.",
    "Zakázané přechody se změnily, postupy se přepočítávají.":
        "The impassable crossings changed, the routes are being recomputed.",
    "občerstvení":
        "refreshment",
    "záměrná zastávka":
        "deliberate stop",
    "ztráta kontaktu s mapou":
        "lost contact with the map",
    "zelenou proběhl":
        "ran through the green",
    "zelenou obíhal":
        "ran around the green",
    "plán %(t)s proti nejlepšímu":
        "plan %(t)s against the best",
    "plán nakreslen":
        "plan drawn",
    "Úsek":
        "Leg",
    "Čas":
        "Time",
    "Oficiálně":
        "Official",
    "Nejlepší":
        "Best",
    "Ztráta":
        "Loss",
    "volbou":
        "by choice",
    "provedením":
        "by execution",
    "Odhad ztráty":
        "Estimated loss",
    "ztráta proti tvému normálu podle mezičasů kategorie":
        "loss against your normal by the splits of the class",
    "Podle mezičasů":
        "By splits",
    "Stání":
        "Standing",
    "Model":
        "Model",
    "Typ chyby":
        "Kind of mistake",
    "Co se stalo":
        "What happened",
    "Vysvětlení":
        "Explanation",
    "postupy jsou vyrovnané":
        "the routes are balanced",
    "Skutečně":
        "Actual",
    "Model je teoretický ideál bez zaváhání, ne čas, který by šel opravdu uběhnout. Ztráta je odhad.":
        "The model is a theoretical ideal without hesitation, not a time that could really be run. The loss is an estimate.",
    "Bez mapy bez tratě nejsou nejlepší postupy. Ztráta je odhad z GPS stopy.":
        "Without the map without course there are no best routes. The loss is an estimate from the GPS track.",
    "Největší časové ztráty":
        "Biggest time losses",
    "Úsek %(name)s":
        "Leg %(name)s",
    "čas %(t)s":
        "time %(t)s",
    "odhad ztráty %(t)s":
        "estimated loss %(t)s",
    "čas <b>%(t)s</b>":
        "time <b>%(t)s</b>",
    "oficiálně %(t)s":
        "official %(t)s",
    "nejlepší postup %(t)s (%(d)s m)":
        "best route %(t)s (%(d)s m)",
    "ztráta volbou %(t)s":
        "loss by choice %(t)s",
    "provedením %(t)s":
        "by execution %(t)s",
    "přímka %(s)s m, běženo %(r)s m":
        "straight line %(s)s m, run %(r)s m",
    "podle mezičasů kategorie %(t)s proti tvému normálu":
        "by the splits of the class %(t)s against your normal",
    "chyba":
        "mistake",
    "Stopa úseku je opravená ručně: ztráta volbou a provedením se počítá po nakreslené čáře, z osobního modelu je úsek vyřazený.":
        "The track of the leg is corrected by hand: the loss by choice and by execution is counted along the drawn line, and the leg is left out of the personal model.",
    "Opravená stopa je uložená, postupy se přepočítávají.":
        "The corrected track is saved, the routes are being recomputed.",
    "Nakreslit stopu znovu":
        "Draw the track again",
    "Opravit moji stopu":
        "Correct my track",
    "nejlepší":
        "best",
    "plán":
        "plan",
    "počítá se…":
        "being computed…",
    "není oceněn":
        "not priced",
    "tvoje stopa":
        "your track",
    "průměrný běžec":
        "average runner",
    "nejlepší postup běžce s průměrným modelem, oceněný tvým modelem":
        "the best route of a runner with the average model, priced by your model",
    "Postup":
        "Route",
    "čas podle tvého modelu rychlosti":
        "time by your speed model",
    "proti nejlepšímu postupu":
        "against the best route",
    "Rozdíl":
        "Difference",
    "Délka":
        "Length",
    "Stoupání":
        "Climb",
    "Všechny časy v tabulce počítá tvůj model rychlosti pro danou čáru, i pro tvoji stopu; naměřený čas úseku je %(t)s.":
        "All times in the table are computed by your speed model for the given line, also for your track; the measured time of the leg is %(t)s.",
    "Plánovaný postup půjde ocenit, až budou u závodu spočítané nejlepší postupy (chybí mapa bez tratě).":
        "The planned route can be priced once the best routes of the race are computed (the map without course is missing).",
    "Čas plánovaného postupu se počítá…":
        "The time of the planned route is being computed…",
    "Plánovaný postup se nepodařilo ocenit. Nakresli ho znovu, nebo spusť v Podkladech analýzu znovu.":
        "The planned route could not be priced. Draw it again, or run the analysis again in Source files.",
    "ke kontrole":
        "to the control",
    "Do 150 m od kontroly není na mapě nic, čeho by se dalo spolehlivě chytit (žádná cesta, voda, budova ani paseka).":
        "Within 150 m of the control there is nothing on the map you could reliably catch onto (no path, water, building or clearing).",
    "Azimuty jsou k severu mapy (magnetické poledníky), tedy rovnou pro buzolu. Body jsou čtené z kresby mapy bez tratě a pojmenované podle mapového klíče ISOM 2017-2: cesty a jejich konce a křížení, voda, budovy, oplocenky a samostatně stojící bodové značky (kupka, jáma, výrazný strom, posed a další). Plot, který nic neuzavírá, čte aplikace jako cestu. „Vrchol“ je z výškového modelu, ne z kresby. Na mapě je zapíná volba „záchytné body“.":
        "Bearings are to the north of the map (magnetic meridians), so ready for the compass. The points are read from the drawing of the map without course and named by the ISOM 2017-2 map key: paths and their ends and junctions, water, buildings, forestry fences and separately standing point symbols (knoll, pit, prominent tree, hunting tower and others). A fence that does not enclose anything is read by the app as a path. “Hilltop” is from the elevation model, not from the drawing. It is switched on on the map by the option “relocating features”.",
    "Popis kontroly:":
        "Control description:",
    "Ztratil jsem se tady: co dělat":
        "I got lost here: what to do",
    "Kdyby ses ztratil":
        "If you got lost",
    "(tady jsi bloudil)":
        "(you were lost here)",
    "Postupy jsou vyrovnané: když se rychlosti v terénu posunou o 20 %, vyjde jako nejlepší jiná varianta. Ztrátu volbou postupu ber jen orientačně.":
        "The routes are balanced: when the speeds in the terrain shift by 20 %, a different variant comes out as the best. Take the loss by route choice only as a rough guide.",
    "Náběhový bod (odhad z mapy, ze směru nejlepšího postupu):":
        "Attack point (an estimate from the map, from the direction of the best route):",
    "před kontrolou není nic, čeho se chytit":
        "there is nothing before the control to catch onto",
    "Zarážka (co potkáš, když kontrolu přeběhneš):":
        "Catching feature (what you meet if you run past the control):",
    "do 200 m za kontrolou není cesta, voda ani nic velkého, co by tě zastavilo":
        "within 200 m beyond the control there is no path, water or anything big that would stop you",
    "Zastávka u občerstvovačky (%(s)s s) se bere jako záměrná automaticky.":
        "A stop at a refreshment control (%(s)s s) counts as deliberate automatically.",
    "Záměrná zastávka: %(s)s s se nepočítá jako chyba.":
        "Deliberate stop: %(s)s s do not count as a mistake.",
    "Na úseku není žádná zastávka delší než 6 s, takže se nic neodečítá.":
        "There is no stop longer than 6 s on the leg, so nothing is subtracted.",
    "Celá ztráta úseku se vede jako chyba, ne jako volba postupu.":
        "The whole loss of the leg is counted as a mistake, not as a route choice.",
    "Ztráta provedením se vede jako únava, ne jako chyba.":
        "The loss by execution is counted as fatigue, not as a mistake.",
    "Únava %(n)s jen popisuje, výpočet nemění.":
        "Fatigue %(n)s only describes, it does not change the computation.",
    "Body stopy, které GPS umístila do zelené, se do modelu nepočítají.":
        "The track points that the GPS put into the green are not counted in the model.",
    "Úsek se počítá do tvého osobního modelu rychlosti.":
        "The leg is counted in your personal speed model.",
    "Úsek se do osobního modelu nepočítá.":
        "The leg is not counted in the personal model.",
    "Uložení se nepovedlo, zkus to znovu.":
        "Saving failed, try again.",
    "Opravená stopa uložená, postupy se přepočítávají.":
        "The corrected track is saved, the routes are being recomputed.",
    "Zpět na GPS stopu, postupy se přepočítávají.":
        "Back to the GPS track, the routes are being recomputed.",
    "Světlý režim":
        "Light mode",
    "Tmavý režim":
        "Dark mode",
    "Režim podle zařízení":
        "Mode follows the device",
    "Nahrávám…":
        "Uploading…",
    "Nahráno, server soubory ukládá…":
        "Uploaded, the server is saving the files…",
    "Soubor je větší, než server přijme.":
        "The file is larger than the server accepts.",
    "Nahrání se nepovedlo (HTTP %(status)s). Zkus to znovu.":
        "Uploading failed (HTTP %(status)s). Try again.",
    "Nahrání se nepovedlo (spojení se přerušilo). Zkus to znovu.":
        "Uploading failed (the connection was interrupted). Try again.",
    "v cíli":
        "at the finish",
    "na kontrole %(n)s":
        "at control %(n)s",
    "ztráta %(t)s na referenci":
        "loss of %(t)s against the reference",
    "%(t)s před referencí":
        "%(t)s ahead of the reference",
    "Start":
        "Start",
    "Cíl":
        "Finish",
    "Kontrola %(name)s":
        "Control %(name)s",
    "bez ražení":
        "no punch",
    "Smazat bod %(name)s":
        "Delete point %(name)s",
    "Klikni na fotce: %(name)s.":
        "Click on the photo: %(name)s.",
    "Vyber v seznamu kontrolu, kterou chceš označit.":
        "Choose in the list the control you want to mark.",
    "Označeno %(n)s z aspoň %(min)s bodů.":
        "Marked %(n)s of at least %(min)s points.",
    "Usazení vychází s odchylkou %(rms)s m, přesnost asi ±%(acc)s m.":
        "The placement comes out with a deviation of %(rms)s m, accuracy about ±%(acc)s m.",
    "Spojení se serverem selhalo, zkus bod posunout znovu.":
        "The connection to the server failed, try moving the point again.",
    "Čekající snímky Livelox už tu nejsou; nahraj je znovu.":
        "The waiting Livelox screenshots are no longer here; upload them again.",
    "Snímek bez tratě je uložený. Až nahraješ snímek s tratí ze stejného pohledu, zpracují se společně.":
        "The screenshot without the course is saved. Upload the course screenshot from the same view and they will be processed together.",
    "Snímky z Livelox jsou uložené a usazují se na pozadí podle běhu a mezičasů. Výsledek uvidíš v úlohách.":
        "The Livelox screenshots are saved and are being placed in the background using the run and split times. See the result in Jobs.",
    "Snímky z Livelox jsou uložené. Jakmile bude k dispozici běh z hodinek a mezičasy z ORIS, usadí se automaticky.":
        "The Livelox screenshots are saved. They will be placed automatically once the watch run and ORIS split times are available.",
    "Snímek s tratí čeká na běh a mezičasy, nebo na zpracování.":
        "The screenshot with the course is waiting for the run and split times, or for processing.",
    "Snímek bez tratě čeká na snímek s tratí ze stejného pohledu.":
        "The screenshot without the course is waiting for the course screenshot from the same view.",
    "Obrázek jde nahrát jen jako mapu s tratí. Mapu bez tratě nahraj jako KMZ z Livelox.":
        "An image can only be uploaded as a map with the course. Upload the map without the course as a KMZ from Livelox.",
    "Fotka je uložená. Až doplníš běh z hodinek a mezičasy z ORIS, usadí se automaticky.":
        "The photo is saved. It will be placed automatically once you add the watch run and ORIS split times.",
    "Fotka je uložená a usazuje se na pozadí; výsledek uvidíš v úlohách.":
        "The photo is saved and is being placed in the background; see the result in Jobs.",
    "1. KMZ z Livelox <span class=\"badge badge-tichy\">nejpřesnější podklady</span>":
        "1. KMZ from Livelox <span class=\"badge badge-tichy\">most accurate source</span>",
    "Mapa s tratí · kategorie %(name)s":
        "Map with course · class %(name)s",
    "Mapa bez tratě · sdílená pro celý závod":
        "Map without course · shared for the whole race",
    "Oba snímky můžeš nahrát najednou, nebo každý zvlášť a klidně před během. Aplikace je uloží a počká na FIT i mezičasy z ORIS. Musí jít o stejný pohled. <a href=\"%(help)s#snimky\">Jak je udělat v Chromu</a>. Jen pro vlastní rozbor, nesdílej je dál.":
        "You can upload both screenshots together or separately, even before the run. The app saves them and waits for the FIT file and ORIS split times. They must show the same view. <a href=\"%(help)s#snimky\">How to make them in Chrome</a>. For your own analysis only; do not share them.",
    "Celou mapu shora, za světla a bez blesku, mapu polož rovně a nic ať nezakrývá kontroly. Fotka se na místo usadí podle kontrol a tvé stopy v oficiálních časech ražení. Můžeš ji nahrát kdykoliv; pokud ještě chybí běh nebo mezičasy z ORIS, počká uložená na jejich doplnění.":
        "Photograph the whole map from above, in daylight and without flash; lay it flat and make sure nothing covers the controls. The photo is placed using the controls and your track at the official punch times. You can upload it at any time; if the run or ORIS splits are missing, it will wait until they are available.",
    "Ke každému závodu appka potřebuje tři věci: běh z hodinek, mapu s tratí a mapu bez tratě. Časy a mezičasy si načte z ORIS sama. KMZ a fotku mapy můžeš nahrát kdykoliv; fotka počká, než bude k dispozici běh a mezičasy. Snímky obrazovky z Livelox můžeš také nahrát kdykoliv a každý zvlášť; aplikace počká na oba snímky, běh a mezičasy z ORIS.":
        "For each race the app needs three things: a watch run, a map with the course and a map without the course. It loads times and splits from ORIS. You can upload a KMZ or map photo at any time; the photo waits until the run and split times are available. Livelox screenshots can also be uploaded at any time, separately; the app waits for both screenshots, the run and the ORIS split times.",
    "Uložená fotka mapy už tu není; nahraj ji znovu.":
        "The saved map photo is no longer here; upload it again.",
    # merged from the branch chain of 2026-11-01 (revize: one main loss number)
    'chyby %(t)s':
        'mistakes %(t)s',
    'rychleji než model o %(t)s':
        'faster than the model by %(t)s',
    'čas nejlepšího postupu podle tvého modelu rychlosti':
        'time of the best route by your speed model',
    'Ideál':
        'Ideal',
    'zvolil jsi pomalejší variantu':
        'you chose a slower option',
    'Volba postupu':
        'Route choice',
    'bloudění, přeběhnutí, kroužení a dohledávání u kontroly, zastavení':
        'getting lost, overshooting, circling and searching near the control, stopping',
    'Chyba':
        'Mistake',
    'ztráta proti tvému obvyklému tempu podle mezičasů kategorie':
        'loss against your usual pace by the class split times',
    'z úseku bez chyby se učí tvůj model rychlosti':
        'your speed model learns from a leg without mistakes',
    'Učí model':
        'Teaches model',
    'model a mezičasy kategorie se tu rozcházejí o víc než minutu':
        'the model and the class split times differ here by more than a minute',
    'víc v panelu úseku':
        'more in the leg panel',
    'Bez ztráty: podle modelu jsi úsek běžel o %(t)s rychleji než nejlepší postup.':
        'No loss: by the model you ran the leg %(t)s faster than the best route.',
    'Bez ztráty (rozdíl do 20 s je v nepřesnosti modelu).':
        "No loss (a difference under 20 s is within the model's accuracy).",
    'Ztráta asi <b>%(t)s</b>':
        'Loss about <b>%(t)s</b>',
    'Smyčky u kontroly se počítají jako chyba, ne jako volba postupu.':
        'Loops near the control count as a mistake, not as route choice.',
    'Stopa vypadá na bloudění, takže se to počítá jako chyba, ne jako volba postupu.':
        'The track looks like getting lost, so it counts as a mistake, not as route choice.',
    'Podle mezičasů kategorie je to %(t)s proti tvému obvyklému tempu. Model a mezičasy se tu rozcházejí, ztrátu z modelu ber s rezervou.':
        'By the class split times it is %(t)s against your usual pace. The model and the split times differ here, take the loss from the model with a pinch of salt.',
    'Odhad ztráty z GPS <b>%(t)s</b>.':
        'Loss estimate from GPS <b>%(t)s</b>.',
    'podle mezičasů kategorie %(t)s proti tvému obvyklému tempu':
        'by the class split times %(t)s against your usual pace',
    'Stopa úseku je opravená ručně: volba postupu a chyba se počítají po nakreslené čáře, z osobního modelu je úsek vyřazený.':
        'The track of the leg is corrected by hand: route choice and mistake are computed along the drawn line, the leg is left out of the personal model.',
    'Varianty jsou skoro stejně rychlé: rozdíl mezi nimi je menší, než jak přesný je model. Obě byly dobrá volba, ztrátu volbou postupu ber jen orientačně.':
        "The options are almost equally fast: the difference between them is smaller than the model's accuracy. Both were a good choice, take the route choice loss only as a rough guide.",
    'chyba a únava %(t)s':
        'mistake and fatigue %(t)s',
    'chyba u kontroly %(t)s':
        'mistake at the control %(t)s',
    'bloudění %(t)s':
        'getting lost %(t)s',
    'chyba v provedení %(t)s':
        'execution mistake %(t)s',
}
