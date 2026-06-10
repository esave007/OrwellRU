#!/usr/bin/env python3
"""Build batch_level3_01.json with translations for first 200 clean strings."""
import json, sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Projects/OrwellRU/originals/level3_clean_strings.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

sorted_data = sorted(data, key=lambda x: x['path_id'])[:200]

# Translation dict: exact EN text -> RU text
# Rules: names stay, dates localized, dialogue by tone, news = formal
T = {}

# Names - keep as-is or transliterate
T["Cassandra Watergate"] = "Кассандра Уотергейт"
T["Mary P."] = "Мэри П."
T["Diane Coleman"] = "Дайан Коулман"
T["Raban Vhart"] = "Рабан Вхарт"
T["Ilya Vhart"] = "Илья Вхарт"
T["Raban"] = "Рабан"
T["Power, Steven"] = "Пауэр, Стивен"
T["Stanford, Lianne"] = "Стэнфорд, Лианна"
T["Ellisson, Rowland"] = "Эллиссон, Роуланд"
T["Collins, Benjamin"] = "Коллинз, Бенджамин"
T["Zacharitas, Silvia"] = "Закаритас, Сильвия"
T["Karen Levine-Vhart"] = "Карен Левин-Вхарт"
T["Shannon Carillo, contributor"] = "Шэннон Карильо, автор"
T["Shannon Carillo, media watchdog"] = "Шэннон Карильо, медиа-обозреватель"
T["Lauren Fitzgerald, M.D.; Bonton"] = "Лорен Фитцджеральд, врач; Бонтон"
T["Raban Vhart, owner"] = "Рабан Вхарт, владелец"
T["Raban Vhart, editor-in-chief"] = "Рабан Вхарт, главный редактор"
T["Ilya Vhart, lead editor"] = "Илья Вхарт, главный редактор"

# Social media handles - keep handles, translate descriptions
T["PeoplesVoice (@PeoplesVoice)"] = "PeoplesVoice (@PeoplesVoice)"
T["PeoplesVoice \r\n(@PeoplesVoice)"] = "PeoplesVoice \r\n(@PeoplesVoice)"
T["Herman Liasov \r\n(@Liasovation)"] = "Герман Лиасов \r\n(@Liasovation)"
T["Not your average weirdo \r\n(@truthseeker23)"] = "Не обычный чудак \r\n(@truthseeker23)"

# Dates - localize months
T["April 3, 2017"] = "3 апреля 2017"
T["April 15, 2017"] = "15 апреля 2017"
T["April 14, 2017\r\nat 11:49 pm"] = "14 апреля 2017\r\n23:49"
T["April 11, 2017 \r\nat 10:52 pm"] = "11 апреля 2017 \r\n22:52"
T["April 14, 2017"] = "14 апреля 2017"
T["March 20, 2017"] = "20 марта 2017"
T["April 13, 2017"] = "13 апреля 2017"
T["April 14"] = "14 апреля"
T["April 09"] = "9 апреля"
T["April 15"] = "15 апреля"
T["April 15, 2017 // Speaker: Raban Vhart // #GoodbyeTPV"] = "15 апреля 2017 // Спикер: Рабан Вхарт // #ПрощайTPV"
T["April 14, 2017 // Speaker: Raban Vhart // #FIGHTtheGov #RESIST"] = "14 апреля 2017 // Спикер: Рабан Вхарт // #ПротивВласти #СОПРОТИВЛЕНИЕ"
T["April 15, 2017 // Author: Raban Vhart // #MEDIAMONSTERS #ruthlessGOV"] = "15 апреля 2017 // Автор: Рабан Вхарт // #МЕДИАмонстры #безжалостнаяВЛАСТЬ"

# Counters - translate words
T["13 likes"] = "13 лайков"
T["235 re-blabbers"] = "235 переблаблов"
T["1 comment"] = "1 комментарий"
T["73 answers"] = "73 ответа"
T["33 likes"] = "33 лайка"
T["85 upvotes"] = "85 голосов"
T["154 answers"] = "154 ответа"
T["213 re-blabbers"] = "213 переблаблов"
T["62 re-blabbers"] = "62 переблабла"
T["89 re-blabbers"] = "89 переблаблов"
T["215 re-blabbers"] = "215 переблаблов"
T["55 answers"] = "55 ответов"
T["93 answers"] = "93 ответа"
T["66 re-blabbers"] = "66 переблаблов"
T["74 re-blabbers"] = "74 переблабла"
T["287 re-blabbers"] = "287 переблаблов"
T["85 re-blabbers"] = "85 переблаблов"
T["64 likes"] = "64 лайка"
T["937 upvotes"] = "937 голосов"
T["617 upvotes"] = "617 голосов"
T["97 upvotes"] = "97 голосов"
T["41 upvotes"] = "41 голос"
T["96 answers"] = "96 ответов"
T["273 answers"] = "273 ответа"
T["35 answers"] = "35 ответов"
T["45 answers"] = "45 ответов"
T["360 upvotes"] = "360 голосов"
T["521 answers"] = "521 ответ"

# Short UI labels
T["Get in touch"] = "Связаться"
T["no connection"] = "нет связи"
T["You"] = "Вы"
T["Soteria"] = "Сотерия"
T["Hologram"] = "Hologram"
T["Your Profile"] = "Ваш профиль"
T["e-ticket"] = "электронный билет"
T["School Principal"] = "Директор школы"
T["Supporting Families"] = "Поддержка семей"
T["Full Screen"] = "Полный экран"
T["[redacted]"] = "[засекречено]"
T["Research Internship"] = "Научная стажировка"
T["Article discussion"] = "Обсуждение статьи"
T["Answer to @LousyLiam"] = "Ответ @LousyLiam"
T["Type"] = "Тип"
T["00:14 am"] = "00:14"
T["Patient date of birth"] = "Дата рождения пациента"
T["Subject"] = "Тема"
T["City Park, Bonton"] = "Городской парк, Бонтон"
T["Your opinions"] = "Ваши мнения"
T["BCC"] = "Копия"
T["Sex:"] = "Пол:"
T["Employee presence"] = "Явка сотрудников"
T["From:"] = "От:"
T["Spiron"] = "Спирон"
T["Back to main menu"] = "Назад в главное меню"
T["Editors"] = "Редакторы"
T["Beautiful"] = "Прекрасно"
T["Upload Documents"] = "Загрузить документы"
T["Scores"] = "Очки"
T["Report:"] = "Отчёт:"
T["Your level: EXPERT"] = "Ваш уровень: ЭКСПЕРТ"
T["From"] = "От"
T["Patient Category"] = "Категория пациента"
T["Patient name"] = "Имя пациента"
T["Patient Number:"] = "Номер пациента:"
T["Volume Sound Effects"] = "Громкость звуковых эффектов"
T["HoB Fan Club Major, 2017"] = "HoB Fan Club Major, 2017"
T["Office Central"] = "Центральный офис"
T["Patient ID: PR-34207"] = "ID пациента: PR-34207"
T["PR-34207"] = "PR-34207"
T["Ok, sorry"] = "Ок, извини"

# Timestamps
T["Posted Wednesday, December 8, 2010, 6:03 am"] = "Опубликовано: среда, 8 декабря 2010, 6:03"
T["Posted Tuesday, February 21, 2006, 5:11 pm"] = "Опубликовано: вторник, 21 февраля 2006, 17:11"
T["16 Apr 17,\r\n02:29 am"] = "16 апр. 17,\r\n02:29"
T["Stephen Sanchez (April 13, 2017 at 05:37 pm):"] = "Стивен Санчес (13 апреля 2017, 17:37):"
T["Ilya Vhart posted on November 27, 2016 at 7:48 pm:"] = "Илья Вхарт опубликовал 27 ноября 2016, 19:48:"

# Registration dates
T["Joined: April 2, 2003"] = "Регистрация: 2 апреля 2003"
T["Joined: September 13, 2007"] = "Регистрация: 13 сентября 2007"

# Social security / IDs
T["Social security number\r\n(issued upon arrival)"] = "Номер соцстрахования\r\n(выдан по прибытии)"
T["Orwell-ID: 438-76-010"] = "Orwell-ID: 438-76-010"

# Short social/game lines
T["Good Spirits\r\nTeahouse"] = "Добрые Духи\r\nЧайная"
T["TPV.blog.PAR - back end"] = "TPV.blog.PAR \u2014 панель управления"
T["CAM ID 0815 1976\r\n2017 APR/13"] = "CAM ID 0815 1976\r\n2017 АПР/13"
T["Pattison,\r\nBill"] = "Паттисон,\r\nБилл"
T["{CHAR_RABAN}"] = "{CHAR_RABAN}"

# News/formal text
T["Grady, Jocelyn / Brotherby Border Checkpoint"] = "Грейди, Джослин / КПП Бразерби"
T["Psychological rehabilitation for PTSD patients"] = "Психологическая реабилитация пациентов с ПТСР"
T["Explosion destroys the Freedom Memorial in Bonton. Three people killed, five severely injured. Authorities receive strange letter."] = "Взрыв разрушил Мемориал Свободы в Бонтоне. Трое погибших, пятеро тяжело ранены. Власти получили странное письмо."
T["11 comments, viewed 291 times"] = "11 комментариев, 291 просмотр"
T["BONTON - Third bombing in Bonton mall averted due to investigative success. Delacroix gives confirmation of efforts."] = "БОНТОН \u2014 Третий теракт в ТЦ Бонтона предотвращён благодаря расследованию. Делакруа подтверждает эффективность мер."
T["Please insert data"] = "Введите данные"
T["Rowland Ellisson:"] = "Роуланд Эллиссон:"
T["Wednesday, April 12: 10:00 - 19:00, laboratory assistance"] = "Среда, 12 апреля: 10:00 - 19:00, помощь в лаборатории"
T["Heavy rainstorms expected for the weekend"] = "На выходных ожидаются сильные ливни"
T["Likewise. :) Being with you is... I dunno what to say... amazing!"] = "Взаимно. :) Быть с тобой \u2014 это... даже не знаю, как сказать... потрясающе!"
T["Creator of The People's Voice, giving truth a chance from the front lines of Parges."] = "Создатель \u00abГолоса Народа\u00bb, дающий правде шанс с передовой Паргеса."
T["I hereby preset you: ACTUAL PROOF of this!"] = "Представляю вам: РЕАЛЬНЫЕ ДОКАЗАТЕЛЬСТВА!"
T["Promoted to 'Corporal'"] = "Повышен до капрала"
T["Woman arrested in connection with recent attacks in Bonton."] = "Женщина арестована в связи с недавними нападениями в Бонтоне."
T["BONTON - The Circle Mall has reportedly been attacked with an explosive device and is being sealed off by the police."] = "БОНТОН \u2014 По информации, ТЦ \u00abСеркл\u00bb атакован взрывным устройством. Территория оцеплена полицией."
T["Know that I stand with you"] = "Знай, что я на твоей стороне"
T["Keep up the great work!"] = "Так держать!"
T["It was my pleasure. I wish you and your family all the best!"] = "Мне было приятно. Всего наилучшего тебе и твоей семье!"
T["Sign up for Singular Pro today!"] = "Подпишитесь на Singular Pro уже сегодня!"
T["Conversation was started by DamnGoodCoffee (35% match)."] = "Разговор начат: DamnGoodCoffee (35% совпадение)."
T["Showing reactions to #ThePeoplesSilencing"] = "Реакции на #ЗамалчиваниеНарода"
T["The order is much bigger than we anticipated."] = "Заказ намного больше, чем мы ожидали."
T["Based on the data you submitted we have learned the following:"] = "На основе предоставленных данных мы установили следующее:"
T["The People's Voice re-blabbered:"] = "\u00abГолос Народа\u00bb переблаблил:"
T["UPLOAD REJECTED: Wrong document type. Please only upload documents about official operations sanctioned by The Nation."] = "ЗАГРУЗКА ОТКЛОНЕНА: Неверный тип документа. Загружайте только документы, санкционированные Нацией."
T["BONTON - Attacks against Stelligan University in Bonton and Freedom Plaza are connected, experts conclude."] = "БОНТОН \u2014 Эксперты установили связь между нападениями на Стеллиганский университет и Площадь Свободы."
T["We said goodbye to our dear home. See you on the other side."] = "Мы попрощались с нашим родным домом. Увидимся на той стороне."
T["Individual match results:"] = "Индивидуальные результаты матча:"
T["Saturday, April 15: 10:00 - 19:00, laboratory assistance"] = "Суббота, 15 апреля: 10:00 - 19:00, помощь в лаборатории"
T["Records of attendance"] = "Журнал посещаемости"
T["Please insert a date."] = "Введите дату."
T["The leading newspaper of The Nation. Fast. Precise. Honest."] = "Ведущая газета Нации. Быстро. Точно. Честно."
T["Veteran of The National Army"] = "Ветеран армии Нации"
T["UPLOAD TO ORWELL"] = "ЗАГРУЗИТЬ В ORWELL"
T["The People's Voice"] = "Голос Народа"
T["Lost connection to Orwell servers"] = "Потеряна связь с серверами Orwell"

# Dialogue / chat
T["Wow, didn't see that coming. Good for you, Ilya! Congrats!"] = "Ого, не ожидал. Молодец, Илья! Поздравляю!"
T['"My daughter stopped talking."'] = "\u00abМоя дочь перестала разговаривать.\u00bb"
T['"The National government KILLS"'] = "\u00abПравительство Нации УБИВАЕТ\u00bb"
T["I agree, and I'm saying this as a Pargesian citizen."] = "Согласен, и говорю это как гражданин Паргеса."
T["Yeah, all good :)"] = "Да, всё хорошо :)"
T["Blaine and Kassart are conspiring against US!"] = "Блейн и Кассарт сговорились ПРОТИВ НАС!"
T["Hi TopdeckLethal!"] = "Привет, TopdeckLethal!"
T["Thank god the government has finally increased the surveillance cams at #FreedomPlaza. I feel much safer there now."] = "Слава богу, правительство наконец увеличило число камер на #ПлощадиСвободы. Теперь чувствую себя там гораздо безопаснее."
T["seriously, since when have you been so good at HoB? "] = "серьёзно, ты когда так хорошо в HoB играть научился? "
T["I can't believe this happened again :("] = "Не могу поверить, что это снова случилось :("
T["I just don't get it. How can anyone sacrifice the lives of innocent people just because they disagree with some laws?"] = "Просто не понимаю. Как можно жертвовать жизнями невинных из-за несогласия с какими-то законами?"
T["Unpopular opinion: Kassart would not be able to manage his country without the great work that prime minister Blaine has been doing in Parges."] = "Непопулярное мнение: Кассарт не смог бы управлять страной без работы, которую премьер Блейн проделала в Паргесе."
T["Our government is corrupt and that is a fact. They have done nothing good for us, or our people so far."] = "Наше правительство коррумпировано, и это факт. Они не сделали ничего хорошего ни для нас, ни для нашего народа."
T["Kassart is NOT who he appears to be."] = "Кассарт \u2014 НЕ тот, кем кажется."

# Social media posts
T["@PeoplesVoice What did you mean when you said Oleg Bakay would \"not be missed\"? Did you \"retire him\"?"] = "@PeoplesVoice Что ты имел в виду, когда сказал, что Олега Бакая \u00abне будут скучать\u00bb? Ты его \u00abубрал\u00bb?"
T["@PeoplesVoice Raban, we stand by you in these difficult times! The people of Parges need you more than ever and we will support you in your fight for the truth! Keep going."] = "@PeoplesVoice Рабан, мы с тобой в эти трудные времена! Народ Паргеса нуждается в тебе больше, чем когда-либо, и мы поддержим тебя в борьбе за правду! Не сдавайся."
T["@PeoplesVoice Your wife should be ashamed. Marrying people who went through traumatic experiences just to keep them under observation is completely unethical. She should lose her license."] = "@PeoplesVoice Твоей жене должно быть стыдно. Выходить замуж за людей, переживших травму, чтобы держать их под наблюдением \u2014 совершенно неэтично. У неё должны отобрать лицензию."
T["@nationalgov What the heck is up with all these goddamn new cameras @FreedomPlaza????!!!! #FuckSurveillance"] = "@nationalgov Какого хрена столько долбаных новых камер на @ПлощадиСвободы????!!!! #ДолойСлежку"
T["@tylr_doubled Back off. Not interested in discussing your wild fantasies."] = "@tylr_doubled Отвали. Не собираюсь обсуждать твои бредни."
T["@DimkaFalak My wife would never do anything like that behind my back."] = "@DimkaFalak Моя жена никогда бы так не поступила за моей спиной."
T['Showing Reactions to "Is anti-Kassart blog involved in Pargesian soldier\'s disappearance?"'] = "Реакции на \u00abПричастен ли антикассартовский блог к исчезновению паргесского солдата?\u00bb"
T["Showing reactions to #SaveKarenAndIlya"] = "Реакции на #СпаситеКаренИИлью"
T["Showing reactions to #CowardBrother"] = "Реакции на #БратТрус"

# News (formal journalistic)
T["BONTON - Explosion at Stelligan University campus kills two students. Is there a connection to yesterday's assault?"] = "БОНТОН \u2014 Взрыв в кампусе Стеллиганского университета унёс жизни двух студентов. Есть ли связь со вчерашним нападением?"
T["TRIFLITH - Prime Minister cancels crisis meeting and instead visits Parges capital. Plans to lead renewal of stalled negotiations between Kassart and Delacroix."] = "ТРИФЛИТ \u2014 Премьер-министр отменяет кризисное совещание и посещает столицу Паргеса. Планирует возобновить переговоры Кассарта и Делакруа."
T["Delacroix presents new crime statistics in a way favoring her politics. But WHO ARE THE REAL CRIMINALS?"] = "Делакруа подаёт статистику преступности в свою пользу. Но КТО НАСТОЯЩИЕ ПРЕСТУПНИКИ?"
T["Catastrophe strikes The Circle Mall, kills one"] = "Катастрофа в ТЦ \u00abСеркл\u00bb \u2014 один погибший"
T["Column author Harrison O'Donnell reflects on last week's article and calls on the citizens of The Nation to show courage in the face of terror."] = "Колумнист Харрисон О'Доннелл размышляет о статье прошлой недели и призывает граждан Нации проявить мужество перед лицом террора."
T["Bonton Police Department announces new prime suspect in Bonton bombings case to be fugitive. Road blocks are being set up in and around Bonton."] = "Полиция Бонтона объявляет главного подозреваемого по делу о взрывах в розыск. Блокпосты устанавливаются по всему городу."

# Long text
T["I am a veteran of the army of The Nation. My career was promising. I served for six years, was in charge of my own squad, and was a well respected combat engineer. I was dishonorably discharged in 2014 for misconduct. It's a decision that I deeply regret."] = "Я ветеран армии Нации. Карьера складывалась многообещающе. Шесть лет службы, командовал собственным отделением, был уважаемым военным инженером. В 2014 году меня с позором уволили за проступок. Это решение, о котором я глубоко сожалею."
T["I am starting to doubt whether TPV represents what I stand for. We sell ourselves as a blog for the Pargesian people, defending their rights and protecting their freedom. As part of that, it is our duty to stand up to our enemies. I don't think we do that any longer."] = "Я начинаю сомневаться, что TPV отстаивает то, во что я верю. Мы позиционируем себя как блог паргесского народа, защищающий его права и свободы. И наш долг \u2014 противостоять врагам. Не думаю, что мы ещё это делаем."
T["Recorded call indicates direct involvement of blog \"The People's Voice\" in the disappearance of <link=\"data_bayte_pargesianofficer\"><color=#575756>Pargesian officer Bayte</color></link>. Further investigation might shed light on Vhart's involvement."] = "Записанный звонок указывает на причастность блога \u00abГолос Народа\u00bb к исчезновению <link=\"data_bayte_pargesianofficer\"><color=#575756>паргесского офицера Бэйта</color></link>. Дальнейшее расследование может прояснить участие Вхарта."
T["We are here to have fun and play Hand of Blood! Come join us, no matter if you are young, old, or immortal and ageless. A special welcome to all entities of the undead!"] = "Мы здесь, чтобы веселиться и играть в Hand of Blood! Присоединяйтесь \u2014 неважно, молоды вы, стары или бессмертны. Особый привет всей нежити!"
T["I am a Pargesian refugee, and crossed the border to The Nation about 9 months ago. I decided to escape the war and flee with my three children after my husband was shot by a sniper.\r\n\r\nThe journey was hard and painful. Sometimes it felt as if we'd never make it. But when we arrived, we were treated with hospitality and shown to temporary accommodation. It made me feel at ease."] = "Я паргесская беженка, пересекла границу Нации около 9 месяцев назад. Я решила бежать от войны с тремя детьми после того, как моего мужа застрелил снайпер.\r\n\r\nПуть был тяжёлым и мучительным. Иногда казалось, что мы не доберёмся. Но когда мы прибыли, нас приняли гостеприимно и определили во временное жильё. Я почувствовала себя в безопасности."
T["Hello Molly.\r\nInsults aside, I think it is quite typical of ex-soldiers to feel that self-help and psychotherapy shows weakness. I find it quite interesting that despite your doubts and prejudices, you still come to our sessions regularly."] = "Здравствуйте, Молли.\r\nОскорбления в сторону, но мне кажется, для бывших военных характерно считать, что самопомощь и психотерапия \u2014 это проявление слабости. И мне интересно, что несмотря на все ваши сомнения и предубеждения, вы всё ещё регулярно приходите на сеансы."
T["We look genuinely happy. The perfect couple, finally moving in together. Life was simply wonderful, and it seemed as if it couldn't get any better. Was it always so great? Sometimes we fought. Well, most of the time, actually."] = "Мы выглядим по-настоящему счастливыми. Идеальная пара, наконец-то переезжаем вместе. Жизнь была прекрасна, казалось, лучше и быть не может. Всегда ли было так? Иногда мы ссорились. Ну, честно говоря, часто."
T["I may have lost this battle, but THE WAR IS NOT OVER. We will fight back against the traitors Kassart and Blaine, who own this manipulative propaganda machine called The National Beholder. YOU WILL PAY FOR THIS."] = "Возможно, я проиграл эту битву, но ВОЙНА НЕ ОКОНЧЕНА. Мы будем сражаться против предателей Кассарта и Блейн, которым принадлежит эта пропагандистская машина под названием The National Beholder. ВЫ ЗА ЭТО ЗАПЛАТИТЕ."
T["Am now proceeding according to the protocol for a situation like this. <link=\"data_bayte_hiding\"><color=#575756>Moving to secret location in the Pargesian mountains</color></link>. We need to talk. No one on the outside should know anything about this."] = "Действую по протоколу для подобных ситуаций. <link=\"data_bayte_hiding\"><color=#575756>Перемещаюсь в тайное место в паргесских горах</color></link>. Нам надо поговорить. Никто посторонний не должен об этом знать."

# Rich text (with link/color tags)
T['<link="website_beholder_foreignconflict2"><#0544AC>Blaine cancels meeting for surprise visit in Triflith</color></link>'] = '<link="website_beholder_foreignconflict2"><#0544AC>Блейн отменяет встречу ради визита в Трифлит</color></link>'
T['<link="website_beholder_dangerdropping"><#0544AC>Crime rate continues to drop</color></link>'] = '<link="website_beholder_dangerdropping"><#0544AC>Уровень преступности продолжает снижаться</color></link>'
T['<link="data_karen_occupation1"><color=#000103>Refugee counselor at Rehab Council</color></link>'] = '<link="data_karen_occupation1"><color=#000103>Консультант по работе с беженцами, Реабилитационный совет</color></link>'
T['<link="data_raban_editorsremoved"><color=#712317>Removed Contributor status from user Daniel</color></link>'] = '<link="data_raban_editorsremoved"><color=#712317>Удалён статус автора у пользователя Daniel</color></link>'
T['<link="website_leaks_bayte"><#0544AC>www.percoleaks.tna - Operation Flying Dog</color></link>'] = '<link="website_leaks_bayte"><#0544AC>www.percoleaks.tna - Операция «Летающий пёс»</color></link>'
T['<link="website_beholder_breakingninadeath"><#0544AC>BREAKING NEWS: Bonton bombings suspect shot on the run</color></link>'] = '<link="website_beholder_breakingninadeath"><#0544AC>СРОЧНО: Подозреваемая в бонтонских взрывах застрелена при попытке бегства</color></link>'
T['<link="website_beholder_firstsuspect"><#0544AC>read more</color></link>'] = '<link="website_beholder_firstsuspect"><#0544AC>читать далее</color></link>'
T['<link="website_beholder_stelliganassaultconnection"><#0544AC>read more</color></link>'] = '<link="website_beholder_stelliganassaultconnection"><#0544AC>читать далее</color></link>'
T['<link="website_beholder_opinion2"><#0544AC>read more</color></link>'] = '<link="website_beholder_opinion2"><#0544AC>читать далее</color></link>'
T['<link="website_beholder_mallsaved"><#0544AC>read more</color></link>'] = '<link="website_beholder_mallsaved"><#0544AC>читать далее</color></link>'
T['<link="website_beholder_movie1"><#0544AC>read more</color></link>'] = '<link="website_beholder_movie1"><#0544AC>читать далее</color></link>'
T['<link="website_beholder_foreignconflict2"><#0544AC>read more</color></link>'] = '<link="website_beholder_foreignconflict2"><#0544AC>читать далее</color></link>'
T['<link="insider_karenspc_mailninadead"><#244B5F>Report on your Patient No. NA-13514 - Nina Maternova</color></link>'] = '<link="insider_karenspc_mailninadead"><#244B5F>Отчёт о вашей пациентке № NA-13514 — Нина Матернова</color></link>'
T['<link="insider_baytephone_phonehistory"><#FFFFFF>Call History</color></link>'] = '<link="insider_baytephone_phonehistory"><#FFFFFF>История звонков</color></link>'
T['<link="data_karen_appointmentthursday"><color=#4312A3>Patient Session Ilya Vhart</color></link>'] = '<link="data_karen_appointmentthursday"><color=#4312A3>Сеанс пациента Ильи Вхарта</color></link>'
T['<link="data_karen_interests"><color=#000103>World Peace, Yoga, Green Tea</color></link>'] = '<link="data_karen_interests"><color=#000103>Мир во всём мире, Йога, Зелёный чай</color></link>'
T['<link="website_peoplesvoice_nationalbeholderdeath"><#F0966E>THE SILENCE of the Government\'s MEDIA LAMBS</color></link>'] = '<link="website_peoplesvoice_nationalbeholderdeath"><#F0966E>МОЛЧАНИЕ правительственных МЕДИА-ЯГНЯТ</color></link>'
T['<link="website_social_karenprofile"><#0082B6>Mrs. Karen Levine-Vhart</color></link>'] = '<link="website_social_karenprofile"><#0082B6>Карен Левин-Вхарт</color></link>'
T['<link="insider_ilyasphone_contacts"><#FFFFFF>Contacts</color></link>'] = '<link="insider_ilyasphone_contacts"><#FFFFFF>Контакты</color></link>'
T['<link="data_karen_address"><color=#3B3B3B>95 Park Avenue, 98-A3 Bonton</color></link>'] = '<link="data_karen_address"><color=#3B3B3B>Парк-авеню, 95, кв. 98-A3, Бонтон</color></link>'

# Rich text with game link data
T['By the way, Uncle Simos wanted to invite <link="data_oleg_neighborraban"><color=#5A5A5A>Oleg Bakay. Just because his family lives next door, doesn\'t mean that we should invite them.</color></link> No way. Let\'s keep it just for our family.'] = 'Кстати, дядя Симос хотел пригласить <link="data_oleg_neighborraban"><color=#5A5A5A>Олега Бакая. Но то, что его семья живёт по соседству, ещё не значит, что мы должны их приглашать.</color></link> Ни за что. Пусть будет только наша семья.'
T['III. THERAPY PROGRESSION\r\n \r\n<link="data_raban_apathetic"><color=#575756>The patient was initially very unresponsive and reclusive, even apathetic in the first session.</color></link> However, after several sessions, Mr. Vhart opened up. He told me about his time in the military, and how he felt serving his home country, Parges.'] = 'III. ДИНАМИКА ТЕРАПИИ\r\n \r\n<link="data_raban_apathetic"><color=#575756>Изначально пациент был крайне замкнут и отрешён, даже апатичен на первом сеансе.</color></link> Однако после нескольких сеансов г-н Вхарт раскрылся. Он рассказал о службе в армии и о своих чувствах, когда служил родине — Паргесу.'
T['<link="data_ilya_liedforraban"><color=#464646>You straight up lying to make me feel better will not change this!</color></link> We are the good guys, bro. We stand up for the Pargesian people. And if that means we need to sacrifice something on the way, so be it. Look at this from the bright side, at least you are safe.'] = '<link="data_ilya_liedforraban"><color=#464646>То, что ты врёшь мне в лицо, чтобы мне стало легче, ничего не изменит!</color></link> Мы хорошие парни, бро. Мы стоим за народ Паргеса. И если ради этого нужно чем-то пожертвовать — пусть так. Смотри на это с яркой стороны: хотя бы ты в безопасности.'
T['David,\r\n\r\nYour loyalty to me is beyond any limits. <link="data_raban_davidlongtime"><color=#FFFFFF>You have been with me from the start. The start was almost 12 years ago.</color></link> It has been a long time, old friend. Thank you.'] = 'Дэвид,\r\n\r\nТвоя преданность мне не знает границ. <link="data_raban_davidlongtime"><color=#FFFFFF>Ты со мной с самого начала. А начало было почти 12 лет назад.</color></link> Много времени прошло, старый друг. Спасибо.'
T['Having a lovely time at #BontonCityPark! <link="data_karen_festivities"><color=#FFFDED>I organized this get-together specifically for the refugees that came to the park.</color></link> We are celebrating life, nature, and each other. Come join us!'] = 'Чудесно проводим время в #ГородскомПаркеБонтона! <link="data_karen_festivities"><color=#FFFDED>Я организовала эту встречу специально для беженцев, пришедших в парк.</color></link> Мы празднуем жизнь, природу и друг друга. Присоединяйтесь!'

# Raban's headline
T["Raban Vhart, owner of @ThePeoplesVoice is a terrible, hateful immigrant who has over stayed his welcome here in The Nation."] = "Рабан Вхарт, владелец @ThePeoplesVoice \u2014 ужасный, злобный иммигрант, злоупотребивший гостеприимством Нации."

# Also handle THE-NATIONAL-BEHOLDER.TNA (keep as URL)
T["THE-NATIONAL-BEHOLDER.TNA"] = "THE-NATIONAL-BEHOLDER.TNA"

# Build final batch matching inventory
batch = {}
matched = 0
unmatched = 0
for e in sorted_data:
    text = e['text']
    if text in T:
        batch[text] = T[text]
        matched += 1
    elif text.rstrip() in T:
        batch[text] = T[text.rstrip()]
        matched += 1
    else:
        # Leave empty - will be handled in later batches
        batch[text] = ''
        unmatched += 1

print(f"Matched: {matched}/{len(sorted_data)}")
print(f"Unmatched: {unmatched}")
if unmatched > 0:
    for k, v in batch.items():
        if v == '':
            t = k.replace('\n', '\\n').replace('\r', '\\r')
            print(f"  MISS: {t[:100]}")

with open('C:/Projects/OrwellRU/translated/batch_level3_01.json', 'w', encoding='utf-8') as f:
    json.dump(batch, f, ensure_ascii=False, indent=2)
print(f"\nSaved batch_level3_01.json with {matched} translations")
