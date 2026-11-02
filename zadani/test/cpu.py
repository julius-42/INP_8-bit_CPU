#------------------------------------------------------------------------------------------------------------
# V teto casti jsou zakladni testy, ktere jsou soucasti zadani
# ===========================================================================================================
# Zasah do teto casti neni dovolen. V pripade, ze potrebujete otestovat funkcnost lepe, zduplikujte si kod 
# testu do uzivatelske casti tohoto skriptu a dopiste pozadovanou funkcionalitu
#------------------------------------------------------------------------------------------------------------
# FIX 17/10/2025 test_fastinit

from scripts.cpu_lib import *

@tb_test()
async def test_reset(dut):
    clk_gen = await cpu_dut_init(dut)
    #aktivovat reset, pockat 50ns, deaktivovat reset
    dut.reset.value = 1
    await Timer(50, units='ns')
    dut.reset.value = 0

    #vyhodnotit stav signalu
    assert (dut.data_en.value.binstr in ['0', '1']), "Invalid enable value"
    assert (dut.done.value.binstr == '0'), "Invalid done value"
    assert (dut.ready.value.binstr == '0'), "Invalid ready value"
    assert ((dut.data_en.value.binstr == '0') or ((dut.data_en.value.binstr == '1') and (dut.data_rdwr.value.binstr == '1'))), "Processor should read from the memory"
    assert (dut.in_req.value.binstr == '0'), "Can't request for input data"
    assert (dut.out_we.value.binstr == '0'), "Can't write to the output" 

@tb_test()
async def test_init(dut):
    """Procesor initialization test"""
    instcnt, mem, _ = await run_program(dut, '@')
    assert (dut.ready.value.binstr == '1'), "Invalid ready value, should be active"
    

@tb_test()
async def test_increment(dut):
    """Increment value of the first memory cell, i.e. *ptr++"""
    instcnt, mem, _ = await run_program(dut, '+++@')
    assert (dut.done.value.binstr == '1'), "Invalid done value, should be active"
    assert instcnt == 4
    assert mem[4] == 3


@tb_test()
async def test_decrement(dut):
    """Decrement value of the first memory cell, i.e. *ptr--"""
    instcnt, mem, _ = await run_program(dut, '---@\3')
    assert instcnt == 4
    assert mem[4] == 0


@tb_test()
async def test_move(dut):
    """Move the pointer to the next cell and increment its value"""
    instcnt, mem, _ = await run_program(dut, '>+@')
    assert instcnt == 3
    assert mem[3] == 0
    assert mem[4] == 1

@tb_test()
async def test_print(dut):
    """Print data to the output, i.e. putchar(*ptr)"""
    instcnt, mem, lcd = await run_program(dut, '...@012', timeout_ns=LCD_WAIT_TIME*5 + 1000)
    assert lcd == "000"

@tb_test()
async def test_input(dut):
    """Load data from the input, i.e. *ptr=getchar()"""
    instcnt, mem, lcd = await run_program(dut, ',,,@', kb_data='312', timeout_ns=(KB_WAIT_TIME+LCD_WAIT_TIME)*5 + 100)
    assert mem[4] == ord('2')

    instcnt, mem, lcd = await run_program(dut, ',,,@', kb_data='123', timeout_ns=(KB_WAIT_TIME+LCD_WAIT_TIME)*5 + 100)
    assert mem[4] == ord('3')


@tb_test()
async def test_while_loop(dut):
    """Simple while loop test"""
    instcnt, mem, lcd = await run_program(dut, '[.-]@\3', timeout_ns = LCD_WAIT_TIME*10)
    assert mem[5] == 0
    assert lcd == "\3\2\1"

@tb_test()
async def test_do_loop(dut):
    """Simple do until loop test"""
    instcnt, mem, lcd = await run_program(dut, '(.-)@\3', timeout_ns = LCD_WAIT_TIME*10)
    assert mem[5] == 0
    assert lcd == "\3\2\1"

@tb_test()
async def test_login(dut, uid=''):
    """Executes program in login.b file"""
    file_name = '../src/login.b'
    assert os.path.isfile(file_name), "File login.b is missing" 
    with open(file_name,'rt') as f:
        prog = f.read()
    assert len(prog), "File login.b doesn't contain any program"
    instcnt, mem, lcd = await run_program(dut, prog, timeout_ns = 250_000)
    lcd = lcd.lower()
    assert lcd == uid, "Invalid output"


#-------------------------------------------------------------------------------------------------------
# Uzivatelske testy
# ===========================================================================================================
# V teto casti muzete v pripade potreby vlozit jakekoliv vlastni testy. 
#-------------------------------------------------------------------------------------------------------


#Odkomentujte jeden z nasledujicich radku pro zarazeni do testu
#@tb_test(skip=True) #test se nespousti automaticky, spustit lze volanim TESTCASE=test_printf make
@tb_test() #test se spousti automaticky
async def test_printf(dut):
    """Program which emulates printing of %d """

    #Priklad testu, ktery provede pozadovany program:
    #Program ocekava vstup z klavesnice, v testu je stisknuta klavesa odpovidajici hodnote 123
    prog = ',#load value and print#[>>+>+<<<-]>>>[<<<+>>>-]<<+>[<->[>++++++++++<[->-[>+>>]>[+[-<+>]>+>>]<<<<<]>[-]++++++++[<++++++>-]>[<<+>>-]>[<<+>>-]<<]>]<[->>++++++++[<++++++>-]]<[.[-]<]<@'
    enableDebug(lcd=True)
    instcnt, mem, lcd = await run_program(dut, prog, kb_data=chr(123), timeout_ns = 1_000_000)
    assert lcd == '123', "Invalid output"

@tb_test()
async def test_ignore_unknown(dut):
    """Neznama instrukce (komentare) se ignoruji"""
    prog = 'a b c+x y z+@'
    instcnt, mem, _ = await run_program(dut, prog, timeout_ns=100_000)
    assert mem[prog.index('@') + 1] == 2
 
 
@tb_test()
async def test_halt_stops(dut):
    """Za znakem @ se nic nevykonava (jsou tam data) a procesor zustane v DONE"""
    prog = '+@+++'
    instcnt, mem, _ = await run_program(dut, prog, timeout_ns=100_000)
    assert dut.done.value.binstr == '1', "Invalid done value, should be active"
    assert mem[2] == ord('+') + 1       # prvni datova bunka byla zvysena instrukci +
    assert mem[3] == ord('+')           # dalsi data nesmi byt zmenena
    assert mem[4] == ord('+')
 
 
@tb_test()
async def test_value_wrap(dut):
    """Preteceni a podteceni 8bitove bunky"""
    prog = '-+>-->' + '+' * 256 + '@'
    base = prog.index('@') + 1
    instcnt, mem, _ = await run_program(dut, prog, timeout_ns=200_000)
    assert mem[base] == 0        # 0 -1 +1
    assert mem[base + 1] == 254  # 0 -2
    assert mem[base + 2] == 0    # 256x +1
 
 
@tb_test()
async def test_ptr_wrap(dut):
    """Ukazatel je kruhovy: 0x0000 <-> 0x1FFF"""
    # [<] jede doleva pres cely program (vsechny znaky jsou nenulove) az na 0x1FFF (nula)
    # tam se zapise 1, pak '>' prejde na adresu 0 a zmeni uz vykonany znak '['
    prog = '[<]+>+@x'
    instcnt, mem, _ = await run_program(dut, prog, timeout_ns=300_000)
    assert mem[0x1FFF] == 1, "Pointer did not wrap from 0x0000 to 0x1FFF"
    assert mem[0] == ord('[') + 1, "Pointer did not wrap from 0x1FFF to 0x0000"
 
 
@tb_test()
async def test_ptr_reads_program(dut):
    """Ukazatel muze ukazovat do programu: < z prvni datove bunky je znak @"""
    instcnt, mem, lcd = await run_program(dut, '<.@', timeout_ns=LCD_WAIT_TIME*2 + 1000)
    assert lcd == '@'
 
 
@tb_test()
async def test_print_moving(dut):
    """Tisk z ruznych bunek"""
    instcnt, mem, lcd = await run_program(dut, '.>.>.@ABC', timeout_ns=LCD_WAIT_TIME*5 + 1000)
    assert lcd == 'ABC'
 
 
@tb_test()
async def test_hello(dut):
    """Prochazeni retezce v datech: [.>]"""
    instcnt, mem, lcd = await run_program(dut, '[.>]@Hello World!', timeout_ns=LCD_WAIT_TIME*14 + 5000)
    assert lcd == 'Hello World!'
 
 
@tb_test()
async def test_input_cells(dut):
    """Cteni do vice bunek a upraveni nactene hodnoty"""
    instcnt, mem, lcd = await run_program(dut, ',>,>,@', kb_data='123', timeout_ns=(KB_WAIT_TIME+LCD_WAIT_TIME)*5 + 1000)
    assert mem[6] == ord('1') and mem[7] == ord('2') and mem[8] == ord('3')
 
    instcnt, mem, lcd = await run_program(dut, ',+.@', kb_data='A', timeout_ns=(KB_WAIT_TIME+LCD_WAIT_TIME)*5 + 1000)
    assert lcd == 'B'
 
 
@tb_test()
async def test_input_loop(dut):
    """Cykl rizeny nactenou hodnotou"""
    instcnt, mem, lcd = await run_program(dut, ',[.-]@', kb_data='\3', timeout_ns=(KB_WAIT_TIME+LCD_WAIT_TIME)*5 + 1000)
    assert lcd == '\3\2\1'
    assert mem[6] == 0
 
 
@tb_test()
async def test_while_skip(dut):
    """Preskok cyklu while: instrukce za ] se musi vykonat (vcetne vnorenych [ ])"""
    instcnt, mem, _ = await run_program(dut, '[-]+@', timeout_ns=100_000)
    assert mem[5] == 1
 
    # prvni znak za [ je dalsi [, celkem se preskoci cele vnejsi telo
    instcnt, mem, _ = await run_program(dut, '[[-]+[>+<-]]>++@', timeout_ns=100_000)
    assert mem[16] == 0 and mem[17] == 2 and mem[18] == 0
 
 
@tb_test()
async def test_do_once(dut):
    """Do-while s nulovou bunkou provede telo prave jednou"""
    instcnt, mem, _ = await run_program(dut, '(>+<)@', timeout_ns=100_000)
    assert mem[6] == 0 and mem[7] == 1 and mem[8] == 0
 
 
@tb_test()
async def test_nested_loops(dut):
    """Vnorene smycky: while ve while (3*4*5), while v do-while a nasledujici smycky za sebou"""
    prog = '+++[>++++[>+++++<-]<-]@'
    base = prog.index('@') + 1
    instcnt, mem, _ = await run_program(dut, prog, timeout_ns=300_000)
    assert [mem[base + i] for i in range(4)] == [0, 0, 60, 0]
 
    prog = '+++(>++[>+<-]<-)@'
    base = prog.index('@') + 1
    instcnt, mem, _ = await run_program(dut, prog, timeout_ns=300_000)
    assert [mem[base + i] for i in range(4)] == [0, 0, 6, 0]
 
    # smycky za sebou: zasobnik musi byt po kazde smycce vyprazdnen
    prog = '++[>+<-]>[>++<-]>[>+++<-]@'
    base = prog.index('@') + 1
    instcnt, mem, _ = await run_program(dut, prog, timeout_ns=300_000)
    assert [mem[base + i] for i in range(5)] == [0, 0, 0, 12, 0]

if __name__=="__main__":
  # call the main function
  print("Run this simulation by calling make.")
  exit()
